"""
Orquestador multi-sesion para Inti.

Permite multiples agentes corriendo en paralelo, cada uno con su propio rol,
modelo LLM y workspace. Los jobs se delegan a sesiones especificas.

Arquitectura:
    Inti Orchestrator
        │
        ├── Session: architect-001 (Sonnet 5, plan, workspace=tenant-x)
        ├── Session: builder-001 (DeepSeek, build, workspace=tenant-x)
        ├── Session: reviewer-001 (Gemini Flash, review, workspace=tenant-x)
        └── Session: builder-002 (DeepSeek, build, workspace=tenant-y)

Cada sesion:
  - Tiene estado (idle, running, completed, error)
  - Se le asignan jobs
  - Puede correr en paralelo con otras sesiones
  - Comparte el bridge (OpenCode server) pero con workspace distinto

Comunicacion:
  - PWA → POST /api/v1/sessions → crea sesion con rol + modelo
  - PWA → POST /api/v1/sessions/{id}/delegate → asigna job a sesion
  - PWA → GET /api/v1/sessions → lista sesiones activas
  - WebSocket → emite SessionStateChanged a la PWA
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Awaitable, Literal

from inti.config import settings

logger = logging.getLogger("inti.orchestrator")

AgentRole = Literal["architect", "builder", "reviewer", "deployer", "custom"]
SessionStatus = Literal["idle", "running", "waiting", "completed", "error", "disconnected"]


@dataclass
class AgentSession:
    """Una sesion de agente activa. Multiples pueden coexistir."""
    id: str
    role: AgentRole
    model: str
    provider: str
    workspace_path: str
    status: SessionStatus = "idle"
    current_job_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)
    task: asyncio.Task | None = field(default=None, repr=False)


ROLE_DEFAULTS: dict[AgentRole, dict] = {
    "architect": {
        "model": "anthropic/claude-sonnet-5",
        "provider": "openrouter",
        "description": "Planifica y disena soluciones. No modifica codigo.",
        "icon": "plan",
        "can_execute": False,
        "can_review": True,
    },
    "builder": {
        "model": settings.loop_model,
        "provider": "openrouter",
        "description": "Ejecuta cambios en el codigo. Modifica archivos.",
        "icon": "build",
        "can_execute": True,
        "can_review": False,
    },
    "reviewer": {
        "model": "google/gemini-2.5-flash",
        "provider": "openrouter",
        "description": "Revisa diffs y ejecuta QA. No modifica codigo.",
        "icon": "review",
        "can_execute": False,
        "can_review": True,
    },
    "deployer": {
        "model": "none",
        "provider": "none",
        "description": "Ejecuta deploys y CI/CD. No usa LLM.",
        "icon": "deploy",
        "can_execute": False,
        "can_review": False,
    },
    "custom": {
        "model": settings.loop_model,
        "provider": "openrouter",
        "description": "Agente personalizado. El usuario elige rol y modelo.",
        "icon": "custom",
        "can_execute": True,
        "can_review": True,
    },
}


class Orchestrator:
    """Gestiona multiples sesiones de agentes en paralelo."""

    def __init__(self):
        self.sessions: dict[str, AgentSession] = {}
        self.max_concurrent: int = 5
        self._emitters: list[Callable[[dict], Awaitable[None]]] = []

    async def load_from_db(self):
        """Carga sesiones desde la DB al iniciar el daemon (persistencia entre reinicios)."""
        try:
            from inti.database import async_session
            from inti.models.agent_session import AgentSession as AgentSessionModel
            from sqlalchemy import select
            async with async_session() as db:
                result = await db.execute(select(AgentSessionModel))
                rows = result.scalars().all()
                for row in rows:
                    self.sessions[row.id] = AgentSession(
                        id=row.id,
                        role=row.role,
                        model=row.model,
                        provider=row.provider,
                        workspace_path=row.workspace_path,
                        status=row.status if row.status in ("idle", "waiting") else "idle",
                        current_job_id=None,
                        created_at=row.created_at or datetime.now(timezone.utc),
                        last_active_at=row.last_active_at,
                        metadata=row.meta_info or {},
                    )
                logger.info(f"Loaded {len(rows)} sessions from DB")
        except Exception:
            logger.warning("Failed to load sessions from DB", exc_info=True)

    def register_emitter(self, emitter: Callable[[dict], Awaitable[None]]):
        """Registra un callback para emitir eventos WebSocket (SessionStateChanged)."""
        self._emitters.append(emitter)

    async def _emit_event(self, event: dict):
        """Emite un evento a todos los WebSockets registrados."""
        for emitter in self._emitters:
            try:
                await emitter(event)
            except Exception:
                logger.warning("Emitter failed", exc_info=True)

    async def _emit_session_changed(self, session: AgentSession):
        """Emite SessionStateChanged al frontend."""
        await self._emit_event({
            "event_type": "SessionStateChanged",
            "job_id": "",
            "version": 1,
            "payload": {
                "session_id": session.id,
                "role": session.role,
                "model": session.model,
                "status": session.status,
                "workspace_path": session.workspace_path,
                "current_job_id": session.current_job_id,
                "metadata": session.metadata,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _persist_session(self, session: AgentSession):
        """Persiste sesion a DB (fire-and-forget)."""
        try:
            from inti.database import async_session
            from inti.models.agent_session import AgentSession as AgentSessionModel
            async with async_session() as db:
                existing = await db.get(AgentSessionModel, session.id)
                if existing:
                    existing.status = session.status
                    existing.current_job_id = session.current_job_id
                    existing.last_active_at = session.last_active_at
                else:
                    db.add(AgentSessionModel(
                        id=session.id,
                        role=session.role,
                        model=session.model,
                        provider=session.provider,
                        status=session.status,
                        workspace_path=session.workspace_path,
                        current_job_id=session.current_job_id,
                        meta_info=session.metadata,
                        created_at=session.created_at,
                        last_active_at=session.last_active_at,
                    ))
                await db.commit()
        except Exception:
            logger.warning("Failed to persist session to DB", exc_info=True)

    def create_session(
        self,
        role: AgentRole,
        model: str | None = None,
        provider: str | None = None,
        workspace_path: str | None = None,
        metadata: dict | None = None,
    ) -> AgentSession:
        import uuid

        defaults = ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["custom"])
        session = AgentSession(
            id=f"{role}-{uuid.uuid4().hex[:8]}",
            role=role,
            model=model or defaults["model"],
            provider=provider or defaults["provider"],
            workspace_path=workspace_path or str(Path.home() / "dopa-workspaces" / "default"),
            metadata=metadata or {},
        )

        active_count = sum(1 for s in self.sessions.values() if s.status in ("running", "waiting"))
        if active_count >= self.max_concurrent:
            session.status = "waiting"

        self.sessions[session.id] = session
        asyncio.ensure_future(self._persist_session(session))
        logger.info(f"Session created: {session.id} [{role}] model={session.model}")
        return session

    def get_session(self, session_id: str) -> AgentSession | None:
        return self.sessions.get(session_id)

    def list_sessions(
        self,
        role: AgentRole | None = None,
        status: SessionStatus | None = None,
    ) -> list[AgentSession]:
        sessions = list(self.sessions.values())
        if role:
            sessions = [s for s in sessions if s.role == role]
        if status:
            sessions = [s for s in sessions if s.status == status]
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def assign_job(self, session_id: str, job_id: str, user_message: str = "") -> bool:
        """Asigna un job a una sesion y spawnea el AgentLoop en background."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        if session.status == "running":
            return False

        session.current_job_id = job_id
        session.status = "running"
        session.last_active_at = datetime.now(timezone.utc)

        # Spawn AgentLoop en background
        task = asyncio.create_task(self._run_session_job(session, job_id, user_message))
        session.task = task

        asyncio.ensure_future(self._persist_session(session))
        asyncio.ensure_future(self._emit_session_changed(session))
        logger.info(f"Job {job_id} assigned to session {session_id} [{session.role}]")
        return True

    async def _run_session_job(self, session: AgentSession, job_id: str, user_message: str):
        """Ejecuta un job en background via AgentLoop."""
        from inti.agent_loop import AgentLoop

        async def emit_wrapper(ev):
            """Wrapper que emite al WebSocket y registra eventos de sesion."""
            # Emitir al WebSocket del cliente
            await self._emit_event(ev)

        try:
            # Cargar el job de la DB para obtener su prompt
            from inti.database import async_session
            from sqlalchemy import select
            from inti.models.job import Job

            prompt = user_message
            try:
                async with async_session() as db:
                    result = await db.execute(select(Job).where(Job.id == job_id))
                    job = result.scalar_one_or_none()
                    if job:
                        prompt = job.description or prompt
            except Exception:
                pass

            workspace = Path(session.workspace_path) if session.workspace_path else Path.cwd()

            loop = AgentLoop(
                workspace=str(workspace),
                model=session.model,
                profile=session.metadata.get("profile"),  # type: ignore[arg-type]
            )
            await loop.run(prompt, emit=emit_wrapper)

            # Job completado
            self.complete_job(session.id, success=True)

        except Exception as e:
            logger.error(f"Session {session.id} job {job_id} failed: {e}", exc_info=True)
            self.complete_job(session.id, success=False)

    def complete_job(self, session_id: str, success: bool = True) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.status = "completed" if success else "error"
        session.current_job_id = None
        session.last_active_at = datetime.now(timezone.utc)
        session.task = None

        self._promote_waiting()
        asyncio.ensure_future(self._persist_session(session))
        asyncio.ensure_future(self._emit_session_changed(session))
        return True

    def disconnect_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.status = "disconnected"
        session.current_job_id = None
        asyncio.ensure_future(self._persist_session(session))
        return True

    def remove_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            # Cancelar task si esta corriendo
            s = self.sessions[session_id]
            if s.task and not s.task.done():
                s.task.cancel()
            del self.sessions[session_id]
            # Borrar de DB
            asyncio.ensure_future(self._delete_session(session_id))
            return True
        return False

    async def _delete_session(self, session_id: str):
        try:
            from inti.database import async_session
            from inti.models.agent_session import AgentSession as AgentSessionModel
            async with async_session() as db:
                existing = await db.get(AgentSessionModel, session_id)
                if existing:
                    await db.delete(existing)
                    await db.commit()
        except Exception:
            logger.warning("Failed to delete session from DB", exc_info=True)

    def get_available_roles(self) -> list[dict]:
        return [
            {"role": role, **defaults}
            for role, defaults in ROLE_DEFAULTS.items()
        ]

    def _promote_waiting(self):
        """Promueve la primera sesion en espera cuando se libera un slot."""
        waiting = [
            s for s in self.sessions.values()
            if s.status == "waiting"
        ]
        if waiting:
            waiting[0].status = "idle"
            logger.info(f"Session promoted from waiting: {waiting[0].id}")

    @property
    def active_count(self) -> int:
        return sum(1 for s in self.sessions.values() if s.status == "running")

    @property
    def total_sessions(self) -> int:
        return len(self.sessions)


orchestrator = Orchestrator()
