from fastapi import APIRouter
from inti.agent_comm import build_agent_message, AgentCommType

router = APIRouter()


@router.post("/send")
async def agent_send(
    from_agent: str = "architect-001",
    from_role: str = "architect",
    comm_type: str = "delegate_task",
    to_agent: str | None = None,
    to_role: str | None = None,
    job_id: str | None = None,
    content: str = "",
):
    msg = build_agent_message(
        from_agent=from_agent,
        from_role=from_role,
        comm_type=comm_type,
        to_agent=to_agent,
        to_role=to_role,
        job_id=job_id,
        content=content,
    )

    from inti.audit import log_action
    await log_action(
        actor_type="llm_architect" if from_role == "architect" else "llm_executor",
        action=f"agent_comm_{comm_type}",
        job_id=job_id,
        summary=f"Agente {from_agent} → {to_role or to_agent}: {comm_type}",
    )

    return {
        "message": msg.to_event(),
        "delivered": True,
    }


@router.get("/templates")
async def list_templates():
    from inti.agent_comm import COMM_TEMPLATES
    return {"templates": [
        {"type": t, "template": v}
        for t, v in COMM_TEMPLATES.items()
    ]}
