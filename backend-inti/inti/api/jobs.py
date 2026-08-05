from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from inti.database import get_db
from inti.models.job import Job
from inti.models.diff import Diff
from inti.policies import TaskProfile, AutonomyLevel, ProjectType, PROFILES
from inti.events import job_state_changed, diff_ready

router = APIRouter()


@router.get("/")
async def list_jobs(
    status: str | None = Query(None),
    profile: str | None = Query(None),
    since: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job)
    if status:
        query = query.where(Job.status == status)
    if profile:
        query = query.where(Job.profile == profile)
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            query = query.where(Job.updated_at > since_dt)
        except ValueError:
            pass
    query = query.order_by(Job.updated_at.desc()).limit(50)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return {
        "jobs": [
            {
                "id": j.id,
                "title": j.title,
                "status": j.status,
                "profile": j.profile,
                "priority": j.priority,
                "autonomy_level": j.autonomy_level,
                "branch_name": j.branch_name,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            }
            for j in jobs
        ],
        "total": len(jobs),
    }


@router.get("/profiles")
async def list_profiles():
    return {
        "profiles": [
            {
                "name": p.name,
                "architect_model": p.architect.model,
                "executor_model": p.executor.model,
                "qa_model": p.qa.model,
                "default_autonomy": p.default_autonomy,
            }
            for p in PROFILES.values()
        ]
    }


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "status": job.status,
        "profile": job.profile,
        "priority": job.priority,
        "autonomy_level": job.autonomy_level,
        "branch_name": job.branch_name,
        "repo_id": job.repo_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.post("/")
async def create_job(
    title: str = Body(...),
    description: str = Body(""),
    profile: TaskProfile = Body("pro_mix"),
    project_type: str = Body(""),
    autonomy_level: AutonomyLevel = Body("human_gatekeeper"),
    db: AsyncSession = Depends(get_db),
):
    actual_profile = project_type if project_type else profile
    job = Job(
        title=title,
        description=description,
        profile=actual_profile,
        autonomy_level=autonomy_level,
        status="planned",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from inti.audit import log_action
    await log_action(
        actor_type="human",
        action="created_job",
        job_id=job.id,
        summary=f"Job creado: {title} (profile={profile})",
    )

    return {
        "job_id": job.id,
        "title": job.title,
        "status": job.status,
        "profile": job.profile,
        "event": job_state_changed(job.id, "", "planned").to_dict(),
    }




@router.post("/{job_id}/approve")
async def approve_job(job_id: str, device_id: str = Body("", embed=False), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    previous = job.status

    # Git commit en el workspace del job
    import subprocess
    ws = (job.repo_id or ".")
    subprocess.run(
        ["git", "commit", "-m", f"Inti: {job.title}"],
        cwd=ws, capture_output=True, text=True,
    )

    job.status = "approved"
    await db.commit()

    # PostMortem best-effort
    try:
        from inti.memory import PostMortem
        await PostMortem.run(job_id)
    except Exception:
        pass

    from inti.audit import log_action
    await log_action(
        actor_type="human",
        action="approved_job",
        job_id=job_id,
        device_id=device_id,
        summary=f"Job {job_id} aprobado/commiteado",
    )

    return {
        "job_id": job.id,
        "status": job.status,
        "event": job_state_changed(job.id, previous, "approved").to_dict(),
    }


@router.post("/{job_id}/reject")
async def reject_job(job_id: str, device_id: str = Body("", embed=False), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    previous = job.status

    # Git discard: revertir working tree a HEAD
    import subprocess
    ws = (job.repo_id or ".")
    subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=ws, capture_output=True, text=True)
    subprocess.run(["git", "clean", "-fd"], cwd=ws, capture_output=True, text=True)

    job.status = "cancelled"
    await db.commit()

    from inti.audit import log_action
    from inti.events import human_approval

    await log_action(
        actor_type="human",
        action="rejected_job",
        job_id=job_id,
        device_id=device_id,
        summary=f"Job {job_id} rechazado",
    )

    return {
        "job_id": job.id,
        "status": job.status,
        "event": human_approval(job.id, "reject", device_id).to_dict(),
    }


@router.get("/{job_id}/diffs")
async def list_diffs(job_id: str, since: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    query = select(Diff).where(Diff.job_id == job_id)
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            query = query.where(Diff.updated_at > since_dt)
        except ValueError:
            pass
    result = await db.execute(query.order_by(Diff.created_at.desc()))
    diffs = result.scalars().all()
    return {
        "diffs": [
            {
                "id": d.id,
                "summary": d.summary,
                "status": d.status,
                "files_changed": d.files_changed,
                "diff_text": d.diff_text,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in diffs
        ],
        "total": len(diffs),
    }


@router.post("/{job_id}/deploy")
async def deploy_job(
    job_id: str,
    environment: str = "production",
    triggered_by: str = "human",
):
    from inti.deploy import DeployService

    result = await DeployService.trigger_deploy(
        job_id=job_id,
        environment=environment,
        triggered_by=triggered_by,
    )
    return result


@router.post("/{job_id}/merge")
async def merge_job(
    job_id: str,
    merge_method: str = "merge",
    device_id: str = "",
):
    from inti.deploy import DeployService

    result = await DeployService.merge_pr(
        job_id=job_id,
        merge_method=merge_method,
        triggered_by="human",
        device_id=device_id,
    )
    return result


@router.get("/{job_id}/ci-status")
async def get_ci_status(job_id: str, db: AsyncSession = Depends(get_db)):
    from inti.models.ci_run import CiRun
    from sqlalchemy import select as sa_select

    result = await db.execute(
        sa_select(CiRun)
        .where(CiRun.job_id == job_id)
        .order_by(CiRun.created_at.desc())
        .limit(5)
    )
    runs = result.scalars().all()
    return {
        "ci_runs": [
            {
                "id": r.id,
                "status": r.status,
                "provider": r.ci_provider,
                "run_id": r.run_id,
                "logs_url": r.logs_url,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in runs
        ],
        "total": len(runs),
    }


@router.post("/ci-webhook")
async def ci_webhook(
    job_id: str,
    status: str,
    provider: str = "github_actions",
    run_id: str | None = None,
    logs_url: str | None = None,
):
    from inti.deploy import DeployService

    result = await DeployService.ci_webhook(
        job_id=job_id,
        status=status,
        provider=provider,
        run_id=run_id,
        logs_url=logs_url,
    )
    return result


@router.post("/deploy-token")
async def set_deploy_token(
    project_id: str,
    token: str,
    endpoint: str | None = None,
):
    from inti.deploy import DeployService

    result = await DeployService.set_deploy_token(
        project_id=project_id,
        token=token,
        endpoint=endpoint,
    )
    return result


@router.post("/{job_id}/execute-graph")
async def execute_graph(job_id: str, workspace_path: str = ""):
    """Ejecuta el pipeline completo via LangGraph FSM (planner → executor → QA paralelo)."""
    from inti.database import async_session
    from sqlalchemy import select
    from inti.models.job import Job

    async with async_session() as db:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return {"error": "Job not found"}

        from inti.langgraph_fsm import build_dopa_code_graph, GraphState
        graph = build_dopa_code_graph()
        state: GraphState = {
            "job_id": job.id,
            "title": job.title,
            "description": job.description or "",
            "profile": job.profile or "general",
            "autonomy_level": "human_gatekeeper",
            "branch_name": "feature/intl",
            "plan": None,
            "execution_result": None,
            "qa_security": None,
            "qa_performance": None,
            "qa_ux": None,
            "qa_aggregated": None,
            "requires_human": True,
            "human_decision": None,
            "deploy_result": None,
            "current_step": "start",
            "errors": [],
            "audit_trail": [],
        }
        if workspace_path:
            state["workspace_path"] = workspace_path  # type: ignore[typeddict-item]

        result_state = await graph.invoke(state)
        return {"status": "completed", "step": result_state["current_step"], "plan": result_state.get("plan"), "execution": result_state.get("execution_result"), "qa": result_state.get("qa_aggregated")}
