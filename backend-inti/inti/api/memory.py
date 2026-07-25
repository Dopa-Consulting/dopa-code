from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from inti.database import get_db
from inti.models.experience_lesson import ExperienceLesson
from inti.models.skill_definition import SkillDefinition
from inti.models.skill_execution import SkillExecution
from inti.models.project_knowledge import ProjectKnowledge
from inti.memory import PostMortem, SkillRefiner, MemoryContext

router = APIRouter()


@router.get("/lessons")
async def list_lessons(
    job_id: str | None = Query(None),
    project_id: str | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(ExperienceLesson)
    if job_id:
        query = query.where(ExperienceLesson.job_id == job_id)
    if project_id:
        query = query.where(ExperienceLesson.project_id == project_id)
    if tag:
        query = query.where(ExperienceLesson.tags_json.ilike(f"%{tag}%"))
    query = query.order_by(ExperienceLesson.created_at.desc()).limit(limit)

    result = await db.execute(query)
    lessons = result.scalars().all()
    return {
        "lessons": [
            {
                "id": l.id,
                "job_id": l.job_id,
                "project_id": l.project_id,
                "lesson_positive": l.lesson_positive,
                "lesson_negative": l.lesson_negative,
                "skill_hint": l.skill_hint,
                "confidence": l.confidence,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in lessons
        ],
        "total": len(lessons),
    }


@router.get("/skills")
async def list_skills(
    min_success_rate: float = Query(0.0, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SkillDefinition)
        .where(SkillDefinition.success_rate >= min_success_rate)
        .order_by(SkillDefinition.success_rate.desc())
        .limit(50)
    )
    skills = result.scalars().all()
    return {
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "steps_json": s.steps_json,
                "best_practices_json": s.best_practices_json,
                "success_rate": s.success_rate,
                "total_executions": s.total_executions,
                "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
            }
            for s in skills
        ],
        "total": len(skills),
    }


@router.get("/skills/{skill_id}/executions")
async def list_skill_executions(
    skill_id: str,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SkillExecution)
        .where(SkillExecution.skill_id == skill_id)
        .order_by(SkillExecution.executed_at.desc())
        .limit(limit)
    )
    execs = result.scalars().all()
    return {
        "executions": [
            {
                "id": e.id,
                "skill_id": e.skill_id,
                "job_id": e.job_id,
                "result": e.result,
                "ci_status": e.ci_status,
                "duration_seconds": e.duration_seconds,
                "executed_at": e.executed_at.isoformat() if e.executed_at else None,
            }
            for e in execs
        ],
        "total": len(execs),
    }


@router.get("/knowledge")
async def list_knowledge(
    project_id: str | None = Query(None),
    key: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(ProjectKnowledge)
    if project_id:
        query = query.where(ProjectKnowledge.project_id == project_id)
    if key:
        query = query.where(ProjectKnowledge.key.ilike(f"%{key}%"))
    query = query.order_by(ProjectKnowledge.updated_at.desc()).limit(50)

    result = await db.execute(query)
    entries = result.scalars().all()
    return {
        "entries": [
            {
                "id": e.id,
                "project_id": e.project_id,
                "key": e.key,
                "value": e.value,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in entries
        ],
        "total": len(entries),
    }


@router.post("/knowledge")
async def set_knowledge(
    project_id: str,
    key: str,
    value: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProjectKnowledge).where(
            ProjectKnowledge.project_id == project_id,
            ProjectKnowledge.key == key,
        )
    )
    entry = result.scalar_one_or_none()
    if entry:
        entry.value = value
    else:
        entry = ProjectKnowledge(project_id=project_id, key=key, value=value)
        db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {
        "id": entry.id,
        "project_id": entry.project_id,
        "key": entry.key,
        "value": entry.value,
    }


@router.post("/postmortem/{job_id}")
async def run_postmortem(job_id: str):
    result = await PostMortem.run(job_id)
    return result


@router.post("/refine-skills")
async def refine_skills(project_id: str | None = None):
    result = await SkillRefiner.run(project_id)
    return result


@router.get("/context/{project_id}")
async def get_memory_context(project_id: str, profile: str = "pro_mix"):
    context = await MemoryContext.get_context_for_job(project_id, profile)
    return {"project_id": project_id, "profile": profile, "context": context}


@router.post("/reseed-skills")
async def reseed_skills():
    from inti.skills_seeder import seed_all_skills
    result = await seed_all_skills()
    return result
