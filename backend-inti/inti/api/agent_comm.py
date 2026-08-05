from fastapi import APIRouter, Body

router = APIRouter()


@router.post("/send")
async def agent_send(
    from_agent: str = Body("architect-001"),
    from_role: str = Body("architect"),
    comm_type: str = Body("delegate_task"),
    to_agent: str | None = Body(None),
    to_role: str | None = Body(None),
    job_id: str | None = Body(None),
    task: str = Body(""),
    plan: str = Body(""),
    summary: str = Body(""),
    question: str = Body(""),
    context: str = Body(""),
    step: str = Body(""),
    details: str = Body(""),
    status: str = Body(""),
    role: str = Body(""),
    model: str = Body(""),
    content: str = Body(""),
):
    """Envia un mensaje de agente a agente via el broker."""
    from inti.agent_comm import build_agent_message, broker

    # Construir kwargs para el template
    template_kwargs = {}
    if comm_type == "delegate_task":
        template_kwargs = {"task": task or content, "plan": plan}
    elif comm_type == "request_review":
        template_kwargs = {"job_id": job_id or "", "summary": summary or content}
    elif comm_type == "query_codebase":
        template_kwargs = {"question": question or content, "context": context}
    elif comm_type == "request_approval":
        template_kwargs = {"step": step, "details": details or content}
    elif comm_type == "report_status":
        template_kwargs = {"job_id": job_id or "", "status": status, "details": details or content}
    elif comm_type == "spawn_agent":
        template_kwargs = {"role": role, "task": task or content, "model": model}
    else:
        template_kwargs = {"content": content}

    msg = build_agent_message(
        comm_type=comm_type,
        from_agent=from_agent,
        from_role=from_role,
        to_agent=to_agent,
        to_role=to_role,
        job_id=job_id,
        **template_kwargs,
    )

    delivered = await broker.send_message(msg)

    from inti.audit import log_action
    await log_action(
        actor_type="llm_architect" if from_role == "architect" else "llm_executor",
        action=f"agent_comm_{comm_type}",
        job_id=msg.job_id,
        summary=f"Agente {from_agent} → {to_role or to_agent}: {comm_type}",
    )

    return {
        "message": msg.to_event(),
        "delivered": delivered,
    }


@router.get("/templates")
async def list_templates():
    from inti.agent_comm import COMM_TEMPLATES
    return {"templates": [
        {"type": t, **v}
        for t, v in COMM_TEMPLATES.items()
    ]}
