import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, func

from inti.config import settings
from inti.database import async_session
from inti.models.experience_lesson import ExperienceLesson
from inti.models.skill_definition import SkillDefinition
from inti.models.skill_execution import SkillExecution
from inti.models.project_knowledge import ProjectKnowledge
from inti.models.job import Job

logger = logging.getLogger("inti.memory")


class PostMortem:
    @staticmethod
    async def run(job_id: str) -> dict:
        if settings.dopa_code_dummy:
            return PostMortem._dummy_result(job_id)

        async with async_session() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return {"error": "Job not found"}

            summary = PostMortem._build_job_summary(job)

            lesson = ExperienceLesson(
                job_id=job_id,
                project_id=job.repo_id,
                tags_json=json.dumps(summary.get("tags", [])),
                lesson_positive=summary.get("positive", "No hay lecciones positivas aun"),
                lesson_negative=summary.get("negative", "No hay lecciones negativas aun"),
                skill_hint=summary.get("skill_hint"),
                confidence=summary.get("confidence", 0.5),
            )
            session.add(lesson)

            if lesson.skill_hint:
                await PostMortem._upsert_skill(session, lesson)

            await session.commit()
            await session.refresh(lesson)

            await PostMortem._generate_doc(job, summary)

            await PostMortem._update_project_knowledge(session, job, summary)

            from inti.audit import log_action
            await log_action(
                actor_type="system",
                action="postmortem_completed",
                job_id=job_id,
                summary=f"Lecciones generadas: {lesson.lesson_positive[:100]}",
            )

            return {
                "lesson_id": lesson.id,
                "positive": lesson.lesson_positive,
                "negative": lesson.lesson_negative,
                "skill_hint": lesson.skill_hint,
                "confidence": lesson.confidence,
            }

    @staticmethod
    def _build_job_summary(job: Job) -> dict:
        return {
            "job_id": job.id,
            "title": job.title,
            "profile": job.profile,
            "status": job.status,
            "tags": [job.profile, "postmortem"],
            "positive": f"Job '{job.title}' completado con perfil {job.profile}.",
            "negative": "Sin incidencias registradas.",
            "skill_hint": None,
            "confidence": 0.6,
        }

    @staticmethod
    async def _upsert_skill(session, lesson: ExperienceLesson) -> None:
        name = lesson.skill_hint[:255]
        result = await session.execute(
            select(SkillDefinition).where(SkillDefinition.name == name)
        )
        skill = result.scalar_one_or_none()

        if skill:
            skill.total_executions += 1
            skill.last_used_at = datetime.now(timezone.utc)
            skill.best_practices_json = json.dumps(
                [lesson.lesson_positive] if lesson.lesson_positive else []
            )
        else:
            skill = SkillDefinition(
                name=name,
                description=f"Skill generada del job {lesson.job_id}",
                steps_json=json.dumps(["analizar", "ejecutar", "verificar"]),
                best_practices_json=json.dumps(
                    [lesson.lesson_positive] if lesson.lesson_positive else []
                ),
                tags_json=lesson.tags_json,
                total_executions=1,
                success_rate=0.5,
                last_used_at=datetime.now(timezone.utc),
            )
            session.add(skill)

        await session.flush()

        execution = SkillExecution(
            skill_id=skill.id,
            job_id=lesson.job_id,
            result="success",
        )
        session.add(execution)

    @staticmethod
    async def _update_project_knowledge(session, job: Job, summary: dict) -> None:
        if not job.repo_id:
            return
        existing = await session.execute(
            select(ProjectKnowledge).where(
                ProjectKnowledge.project_id == job.repo_id,
                ProjectKnowledge.key == f"last_job_{job.profile}",
            )
        )
        entry = existing.scalar_one_or_none()
        if entry:
            entry.value = f"Ultimo job: {job.title} ({job.status})"
            entry.updated_at = datetime.now(timezone.utc)
        else:
            entry = ProjectKnowledge(
                project_id=job.repo_id,
                key=f"last_job_{job.profile}",
                value=f"Ultimo job: {job.title} ({job.status})",
            )
            session.add(entry)

    @staticmethod
    async def _generate_doc(job: Job, summary: dict) -> None:
        try:
            project_root = Path(__file__).parent.parent.parent
            history_dir = project_root / "docs" / "dopa-code-history"
            ts = datetime.now(timezone.utc).strftime("%Y-%m")
            history_dir.joinpath(ts).mkdir(parents=True, exist_ok=True)

            doc_path = history_dir / ts / f"job-{job.id[:8]}.md"
            content = f"""# Job: {job.title}

- **ID**: {job.id}
- **Perfil**: {job.profile}
- **Estado**: {job.status}
- **Nivel de autonomia**: {job.autonomy_level}
- **Creado**: {job.created_at}
- **Actualizado**: {job.updated_at}

## Descripcion

{job.description or 'Sin descripcion'}

## Lecciones

- **Positivo**: {summary.get('positive', 'N/A')}
- **Negativo**: {summary.get('negative', 'N/A')}

## Skill sugerida

{summary.get('skill_hint', 'Ninguna')}

---
*Generado automaticamente por Inti - {datetime.now(timezone.utc).isoformat()}
"""
            doc_path.write_text(content, encoding="utf-8")
            logger.info(f"Postmortem doc saved: {doc_path}")
        except Exception as e:
            logger.warning(f"Failed to save postmortem doc: {e}")

    @staticmethod
    def _dummy_result(job_id: str) -> dict:
        return {
            "lesson_id": f"dummy-{job_id[:8]}",
            "positive": "[DUMMY] El plan fue claro y los tests pasaron a la primera.",
            "negative": "[DUMMY] Se olvido actualizar migraciones.",
            "skill_hint": "refactor-con-migraciones",
            "confidence": 0.8,
        }


class SkillRefiner:
    @staticmethod
    async def run(project_id: str | None = None) -> dict:
        if settings.dopa_code_dummy:
            return {"message": "[DUMMY] Skill refinement skipped", "skills_updated": 0}

        async with async_session() as session:
            query = select(SkillDefinition)
            if project_id:
                query = query.where(
                    SkillDefinition.tags_json.ilike(f"%{project_id}%")
                )
            result = await session.execute(query)
            skills = result.scalars().all()

            updated = 0
            for skill in skills:
                execs_result = await session.execute(
                    select(SkillExecution)
                    .where(SkillExecution.skill_id == skill.id)
                    .limit(50)
                )
                executions = execs_result.scalars().all()
                total = len(executions)
                successes = sum(1 for e in executions if e.result == "success")
                skill.success_rate = successes / total if total > 0 else 0.0
                skill.total_executions = total
                updated += 1

            await session.commit()

            from inti.audit import log_action
            await log_action(
                actor_type="system",
                action="skill_refinement",
                summary=f"Refinadas {updated} skills",
            )

            return {"message": f"{updated} skills refinadas", "skills_updated": updated}


class MemoryContext:
    @staticmethod
    async def get_context_for_job(
        project_id: str | None,
        profile: str,
        limit: int = 5,
    ) -> str:
        if settings.dopa_code_dummy:
            return "[DUMMY] Contexto simulado: las skills han funcionado bien en el pasado."

        async with async_session() as session:
            result = await session.execute(
                select(SkillDefinition)
                .where(
                    SkillDefinition.tags_json.ilike(f"%{profile}%")
                    if project_id
                    else True
                )
                .order_by(SkillDefinition.success_rate.desc())
                .limit(limit)
            )
            skills = result.scalars().all()

            lines = ["## Contexto de memoria\n"]
            for s in skills:
                lines.append(
                    f"- **{s.name}** (exito: {s.success_rate:.0%}, "
                    f"{s.total_executions} ejecuciones): {s.description}"
                )

            lessons_result = await session.execute(
                select(ExperienceLesson)
                .where(
                    ExperienceLesson.project_id == project_id
                    if project_id
                    else True
                )
                .order_by(ExperienceLesson.created_at.desc())
                .limit(limit)
            )
            lessons = lessons_result.scalars().all()

            if lessons:
                lines.append("\n## Lecciones previas\n")
                for l in lessons:
                    if l.lesson_negative:
                        lines.append(f"- [Evitar] {l.lesson_negative}")

            knowledge_result = await session.execute(
                select(ProjectKnowledge).where(
                    ProjectKnowledge.project_id == project_id
                    if project_id
                    else True
                ).limit(10)
            )
            knowledge = knowledge_result.scalars().all()
            if knowledge:
                lines.append("\n## Conocimiento del proyecto\n")
                for k in knowledge:
                    lines.append(f"- {k.key}: {k.value}")

            return "\n".join(lines)
