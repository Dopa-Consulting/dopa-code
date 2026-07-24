from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inti.database import get_db
from inti.models.job import Job
from inti.models.diff import Diff
from inti.policies import TaskProfile, AutonomyLevel, get_profile, PROFILES
from inti.events import job_state_changed, diff_ready

router = APIRouter()


@router.get("/")
async def list_jobs(
    status: str | None = Query(None),
    profile: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job)
    if status:
        query = query.where(Job.status == status)
    if profile:
        query = query.where(Job.profile == profile)
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
    title: str,
    description: str = "",
    profile: TaskProfile = "pro_mix",
    autonomy_level: AutonomyLevel = "human_gatekeeper",
    db: AsyncSession = Depends(get_db),
):
    job = Job(
        title=title,
        description=description,
        profile=profile,
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


@router.post("/{job_id}/start")
async def start_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    previous = job.status
    job.status = "executing"
    await db.commit()

    from inti.agent_runtime import agent_runtime
    profile_config = get_profile(job.profile)
    plan_result = agent_runtime.plan_change(job_id, job.description)

    return {
        "job_id": job.id,
        "status": job.status,
        "profile": profile_config.name,
        "architect_model": profile_config.architect.model,
        "plan": plan_result,
        "event": job_state_changed(job.id, previous, "executing").to_dict(),
    }


@router.post("/{job_id}/approve")
async def approve_job(job_id: str, device_id: str = "", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    previous = job.status
    job.status = "approved"
    await db.commit()

    from inti.audit import log_action
    from inti.events import human_approval

    await log_action(
        actor_type="human",
        action="approved_job",
        job_id=job_id,
        device_id=device_id,
        summary=f"Job {job_id} aprobado",
    )

    return {
        "job_id": job.id,
        "status": job.status,
        "event": human_approval(job.id, "approve", device_id).to_dict(),
    }


@router.post("/{job_id}/reject")
async def reject_job(job_id: str, device_id: str = "", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    previous = job.status
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
async def list_diffs(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Diff).where(Diff.job_id == job_id).order_by(Diff.created_at.desc())
    )
    diffs = result.scalars().all()
    return {
        "diffs": [
            {
                "id": d.id,
                "summary": d.summary,
                "status": d.status,
                "files_changed": d.files_changed,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in diffs
        ],
        "total": len(diffs),
    }
