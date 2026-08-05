"""
Comunicacion agente-a-agente para Dopa Code.

Permite que el arquitecto delegue tareas al builder, el builder pida review,
y el reviewer apruebe/rechace cambios. Los mensajes fluyen a traves de colas
asyncio por sesion con persistencia en conversation_messages.

Formato de mensaje:
    Architect → Builder: "implementa el plan de checkout"
    Builder → Reviewer: "revisa este diff"
    Reviewer → Architect: "QA: diff aprobado"
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("inti.agent_comm")

COMM_TEMPLATES = {
    "delegate_task": {
        "template": "Te delego la tarea: {task}. Plan: {plan}",
        "description": "Delegar tarea de arquitecto a builder",
    },
    "request_review": {
        "template": "Por favor revisa el diff del job {job_id}: {summary}",
        "description": "Builder solicita revision del reviewer",
    },
    "query_codebase": {
        "template": "Consulta sobre el codigo: {question}. Contexto: {context}",
        "description": "Pregunta sobre patrones o arquitectura",
    },
    "request_approval": {
        "template": "Solicito aprobacion para continuar con {step}. Detalles: {details}",
        "description": "Agente solicita aprobacion humana",
    },
    "report_status": {
        "template": "Estado de {job_id}: {status}. {details}",
        "description": "Builder reporta estado al arquitecto",
    },
    "spawn_agent": {
        "template": "Necesito un agente {role} para {task} con modelo {model}",
        "description": "Solicita crear un nuevo agente",
    },
}


@dataclass
class AgentMessage:
    id: str
    from_agent: str | None
    from_role: str | None
    to_agent: str | None
    to_role: str | None
    comm_type: str
    content: str
    job_id: str | None = None
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_event(self) -> dict:
        return {
            "event_type": "AgentCommunication",
            "job_id": self.job_id or "",
            "version": 1,
            "payload": {
                "message_id": self.id,
                "from_agent": self.from_agent,
                "from_role": self.from_role,
                "to_agent": self.to_agent,
                "to_role": self.to_role,
                "type": self.comm_type,
                "content": self.content,
                "metadata": self.metadata,
            },
            "timestamp": self.timestamp,
        }


def build_agent_message(
    comm_type: str,
    from_agent: str | None = None,
    from_role: str | None = None,
    to_agent: str | None = None,
    to_role: str | None = None,
    job_id: str | None = None,
    metadata: dict | None = None,
    **kwargs,
) -> AgentMessage:
    import uuid
    template = COMM_TEMPLATES.get(comm_type, {}).get("template", "{content}")
    content = template.format(**kwargs)
    return AgentMessage(
        id=f"msg-{uuid.uuid4().hex[:12]}",
        from_agent=from_agent,
        from_role=from_role,
        to_agent=to_agent,
        to_role=to_role,
        comm_type=comm_type,
        content=content,
        job_id=job_id,
        metadata=metadata or {},
    )


class AgentCommBroker:
    """Cola de mensajes agente-a-agente con persistencia."""

    def __init__(self):
        self._queues: dict[str, asyncio.Queue[AgentMessage]] = {}
        self._emitters: list = []

    def register_emitter(self, emitter):
        self._emitters.append(emitter)

    def get_queue(self, session_id: str) -> asyncio.Queue[AgentMessage]:
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue(maxsize=100)
        return self._queues[session_id]

    async def send_message(self, msg: AgentMessage) -> bool:
        """Envia un mensaje a uno o mas destinatarios. Persiste en DB."""
        delivered = False

        # Persistir en conversation_messages
        try:
            from inti.database import async_session
            from inti.models.conversation_message import ConversationMessage
            async with async_session() as db:
                db.add(ConversationMessage(
                    session_id=msg.to_agent or "broadcast",
                    role=msg.from_role or "system",
                    content=f"[{msg.comm_type}] {msg.content}",
                ))
                await db.commit()
        except Exception:
            logger.warning("Failed to persist agent message", exc_info=True)

        # Enviar a destinatario especifico
        if msg.to_agent and msg.to_agent in self._queues:
            try:
                self._queues[msg.to_agent].put_nowait(msg)
                delivered = True
            except asyncio.QueueFull:
                logger.warning(f"Queue full for session {msg.to_agent}")

        # Broadcast a rol especifico
        if msg.to_role:
            from inti.orchestrator import orchestrator
            sessions = orchestrator.list_sessions(role=msg.to_role)
            for s in sessions:
                if s.id in self._queues:
                    try:
                        self._queues[s.id].put_nowait(msg)
                        delivered = True
                    except asyncio.QueueFull:
                        pass

        # Emitir evento WebSocket para notificar
        event = msg.to_event()
        for emitter in self._emitters:
            try:
                await emitter(event)
            except Exception:
                pass

        return delivered

    async def receive_message(self, session_id: str) -> AgentMessage | None:
        """Devuelve el siguiente mensaje para una sesion (non-blocking)."""
        q = self.get_queue(session_id)
        try:
            return q.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def remove_session(self, session_id: str):
        if session_id in self._queues:
            del self._queues[session_id]


broker = AgentCommBroker()
