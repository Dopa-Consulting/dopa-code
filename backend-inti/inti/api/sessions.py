from fastapi import APIRouter, Query, Body

from inti.orchestrator import orchestrator, AgentRole, SessionStatus

router = APIRouter()


@router.get("/")
async def list_sessions(
    role: str | None = Query(None),
    status: str | None = Query(None),
):
    sessions = orchestrator.list_sessions(
        role=role,
        status=status,
    )
    return {
        "sessions": [
            {
                "id": s.id,
                "role": s.role,
                "model": s.model,
                "provider": s.provider,
                "status": s.status,
                "workspace_path": s.workspace_path,
                "current_job_id": s.current_job_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
            }
            for s in sessions
        ],
        "total": len(sessions),
        "active": orchestrator.active_count,
        "max_concurrent": orchestrator.max_concurrent,
    }


@router.get("/roles")
async def list_roles():
    return {"roles": orchestrator.get_available_roles()}


@router.post("/")
async def create_session(
    role: str = Body("builder"),
    model: str | None = Body(None),
    provider: str | None = Body(None),
    workspace_path: str | None = Body(None),
):
    if role not in ["architect", "builder", "reviewer", "deployer", "custom"]:
        return {"error": f"Invalid role: {role}. Use: architect, builder, reviewer, deployer, custom"}

    session = orchestrator.create_session(
        role=role,
        model=model,
        provider=provider,
        workspace_path=workspace_path,
    )
    return {
        "session_id": session.id,
        "role": session.role,
        "model": session.model,
        "status": session.status,
        "workspace_path": session.workspace_path,
    }


@router.get("/{session_id}")
async def get_session(session_id: str):
    session = orchestrator.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    return {
        "id": session.id,
        "role": session.role,
        "model": session.model,
        "provider": session.provider,
        "status": session.status,
        "workspace_path": session.workspace_path,
        "current_job_id": session.current_job_id,
        "metadata": session.metadata,
    }


@router.post("/{session_id}/delegate")
async def delegate_job(session_id: str, job_id: str):
    """Asigna un job a una sesion especifica. La sesion lo ejecuta con su modelo."""
    ok = orchestrator.assign_job(session_id, job_id)
    if not ok:
        return {"error": "Cannot assign job. Session busy or not found."}

    session = orchestrator.get_session(session_id)

    from inti.audit import log_action
    await log_action(
        actor_type="human",
        action="job_delegated",
        job_id=job_id,
        summary=f"Job {job_id} delegado a sesion {session_id} [{session.role}] model={session.model}",
    )

    return {
        "status": "delegated",
        "session_id": session_id,
        "job_id": job_id,
        "agent_role": session.role,
        "model": session.model,
    }


@router.post("/{session_id}/complete")
async def complete_session(session_id: str, success: bool = True):
    ok = orchestrator.complete_job(session_id, success)
    if not ok:
        return {"error": "Session not found"}
    return {"status": "completed" if success else "error", "session_id": session_id}


@router.delete("/{session_id}")
async def remove_session(session_id: str):
    ok = orchestrator.remove_session(session_id)
    return {"status": "removed" if ok else "not_found", "session_id": session_id}
