"""
Agente-a-agente: comunicacion entre sesiones del Orchestrator.

Casos de uso:
  1. Architect -> Builder: delegar ejecucion de un plan
  2. Builder -> Reviewer: solicitar revision de diff
  3. Architect -> Reviewer: consultar patrones en el codebase
  4. Cualquier agente -> Human: solicitar aprobacion
  5. Orchestrator -> Builder: spawner un builder para arreglar un bug

Flujo:
  Agente A (via API/PWA) -> POST /api/v1/agent-comm -> Inti
  Inti -> WebSocket -> Agente B (notificacion)
  Agente B -> procesa -> responde
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

AgentCommType = Literal[
    "delegate_task",
    "request_review",
    "query_codebase",
    "request_approval",
    "report_status",
    "spawn_agent",
]


@dataclass
class AgentMessage:
    id: str
    from_agent: str
    from_role: str
    to_agent: str | None
    to_role: str | None
    comm_type: AgentCommType
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
                "comm_type": self.comm_type,
                "content": self.content,
                "metadata": self.metadata,
            },
            "timestamp": self.timestamp,
        }


COMM_TEMPLATES: dict[AgentCommType, str] = {
    "delegate_task": "Ejecuta el siguiente plan sobre el workspace {workspace}:\n\n{plan}",
    "request_review": "Revisa el diff del job {job_id}:\n\n{diff_summary}",
    "query_codebase": "Busca en {workspace} informacion sobre: {query}",
    "request_approval": "Solicito aprobacion para {action} en job {job_id}",
    "report_status": "Estado de {agent}: {status}. Job actual: {job_id}",
    "spawn_agent": "Crear agente {role} con modelo {model} para {reason}",
}


def build_agent_message(
    from_agent: str,
    from_role: str,
    comm_type: AgentCommType,
    to_agent: str | None = None,
    to_role: str | None = None,
    job_id: str | None = None,
    **kwargs,
) -> AgentMessage:
    import uuid
    template = COMM_TEMPLATES.get(comm_type, "{content}")
    content = template.format(**kwargs)

    return AgentMessage(
        id=uuid.uuid4().hex[:12],
        from_agent=from_agent,
        from_role=from_role,
        to_agent=to_agent,
        to_role=to_role,
        comm_type=comm_type,
        content=content,
        job_id=job_id,
        metadata=kwargs,
    )
