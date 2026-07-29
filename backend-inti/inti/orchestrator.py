"""
Orquestador multi-sesion para Inti.

Permite multiples agentes corriendo en paralelo, cada uno con su propio rol,
modelo LLM y workspace. Los jobs se delegan a sesiones especificas.

Arquitectura:
    Inti Orchestrator
        │
        ├── Session: architect-001 (Opus 4.8, plan, workspace=tenant-x)
        ├── Session: builder-001 (DeepSeek, build, workspace=tenant-x)
        ├── Session: reviewer-001 (Gemini 3.6, review, workspace=tenant-x)
        └── Session: builder-002 (Sonnet 5, build, workspace=tenant-y)

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
from enum import Enum
from pathlib import Path
from typing import Literal

from inti.config import settings

logger = logging.getLogger("inti.orchestrator")

SESSION_FILE = Path(__file__).parent.parent / "sessions.json"

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


ROLE_DEFAULTS: dict[AgentRole, dict] = {
    "architect": {
        "model": "anthropic/claude-opus-4-8",
        "provider": "openrouter",
        "description": "Planifica y disena soluciones. No modifica codigo.",
        "icon": "plan",
        "can_execute": False,
        "can_review": True,
    },
    "builder": {
        "model": "deepseek/deepseek-chat",
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
        "model": "deepseek/deepseek-chat",
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
        self._load_from_file()

    def _persist_to_file(self):
        """Guarda sesiones a JSON para sobrevivir reinicios del daemon."""
        try:
            data = {}
            for sid, s in self.sessions.items():
                data[sid] = {
                    "id": s.id,
                    "role": s.role,
                    "model": s.model,
                    "provider": s.provider,
                    "status": s.status,
                    "workspace_path": s.workspace_path,
                    "current_job_id": s.current_job_id,
                    "metadata": s.metadata,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
                }
            SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.warning("Failed to persist sessions", exc_info=True)

    def _load_from_file(self):
        """Carga sesiones desde JSON al iniciar el daemon."""
        if not SESSION_FILE.exists():
            return
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for sid, sdata in data.items():
                self.sessions[sid] = AgentSession(
                    id=sdata.get("id", sid),
                    role=sdata.get("role", "builder"),
                    model=sdata.get("model", ""),
                    provider=sdata.get("provider", ""),
                    status=sdata.get("status", "idle"),
                    workspace_path=sdata.get("workspace_path", ""),
                    current_job_id=sdata.get("current_job_id"),
                    metadata=sdata.get("metadata", {}),
                    created_at=datetime.fromisoformat(sdata["created_at"]) if sdata.get("created_at") else datetime.now(timezone.utc),
                    last_active_at=datetime.fromisoformat(sdata["last_active_at"]) if sdata.get("last_active_at") else None,
                )
            logger.info(f"Loaded {len(self.sessions)} sessions from {SESSION_FILE}")
        except Exception:
            logger.warning("Failed to load sessions", exc_info=True)

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
        self._persist_to_file()
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

    def assign_job(self, session_id: str, job_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        if session.status == "running":
            return False
        session.current_job_id = job_id
        session.status = "running"
        session.last_active_at = datetime.now(timezone.utc)
        self._persist_to_file()
        return True

    def complete_job(self, session_id: str, success: bool = True) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.status = "completed" if success else "error"
        session.current_job_id = None
        session.last_active_at = datetime.now(timezone.utc)

        self._promote_waiting()
        self._persist_to_file()
        return True

    def disconnect_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.status = "disconnected"
        session.current_job_id = None
        self._persist_to_file()
        return True

    def remove_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._persist_to_file()
            return True
        return False

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
