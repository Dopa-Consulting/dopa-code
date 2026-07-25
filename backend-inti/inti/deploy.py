import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx

from inti.config import settings
from inti.database import async_session
from inti.models.job import Job
from inti.models.ci_run import CiRun
from inti.models.project_knowledge import ProjectKnowledge
from sqlalchemy import select

logger = logging.getLogger("inti.deploy")


class PreDeployAudit:
    """Pre-deploy audit checklist. Adaptado de Hainrixz/all-deploy (MIT)."""

    @staticmethod
    async def run(job_id: str, workspace_path: str) -> dict:
        findings: list[dict] = []
        critical_violations: list[dict] = []
        import subprocess
        from pathlib import Path

        ws = Path(workspace_path)

        # 1. .gitignore exist
        gitignore = ws / ".gitignore"
        if not gitignore.exists():
            critical_violations.append({
                "check": "no_gitignore",
                "message": "No .gitignore found",
                "fix": "Create .gitignore with node_modules, .env, dist, build",
            })

        # 2. .env tracked?
        env_file = ws / ".env"
        if env_file.exists():
            try:
                result = subprocess.run(
                    ["git", "ls-files", "--error-unmatch", ".env"],
                    cwd=str(ws), capture_output=True, timeout=5,
                )
                if result.returncode == 0:
                    critical_violations.append({
                        "check": "env_tracked",
                        "message": ".env is tracked by git - secrets exposed!",
                        "fix": "git rm --cached .env && add .env to .gitignore",
                    })
            except Exception:
                pass

        # 3. .env.example exists
        env_example = ws / ".env.example"
        if not env_example.exists():
            critical_violations.append({
                "check": "no_env_example",
                "message": ".env.example missing. Document all env vars.",
                "fix": "Create .env.example with all required vars (see quickstart.ps1)",
            })

        # 4. Working tree clean
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(ws), capture_output=True, timeout=5,
            )
            if result.stdout.strip():
                critical_violations.append({
                    "check": "dirty_tree",
                    "message": "Working tree is not clean",
                    "fix": "Commit or stash changes before deploy",
                    "details": result.stdout.decode()[:200],
                })
        except Exception:
            pass

        # 5. Lockfile present for Node projects
        pkg_json = ws / "package.json"
        if pkg_json.exists():
            lockfiles = ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb"]
            if not any((ws / lf).exists() for lf in lockfiles):
                critical_violations.append({
                    "check": "no_lockfile",
                    "message": "No lockfile found. Dependencies not pinned.",
                    "fix": "Run: npm install (or yarn/pnpm/bun install)",
                })

        # 6. Localhost binding check
        try:
            for py_file in ws.rglob("*.py"):
                if py_file.name.startswith("."):
                    continue
                content = py_file.read_text(errors="ignore")
                if "127.0.0.1" in content and ("uvicorn" in content or "app.run" in content or "flask run" in content):
                    findings.append({
                        "check": "localhost_binding",
                        "message": f"{py_file.name} binds to 127.0.0.1 - may not work on remote hosts",
                        "severity": "warning",
                    })
                    break
        except Exception:
            pass

        passed = len(critical_violations) == 0

        if not passed:
            logger.warning(
                f"Pre-deploy audit FAILED for job {job_id}: "
                f"{len(critical_violations)} critical issues"
            )

        return {
            "passed": passed,
            "critical": critical_violations,
            "warnings": findings,
            "message": "Audit passed" if passed else f"{len(critical_violations)} critical issues block deploy",
        }


class DeployService:

    @staticmethod
    async def trigger_deploy(
        job_id: str,
        environment: str = "production",
        triggered_by: str = "human",
    ) -> dict:
        if settings.dopa_code_dummy:
            return DeployService._dummy_deploy(job_id, environment)

        # Pre-deploy audit (skip only if explicitly bypassed)
        if environment == "production" and triggered_by != "force":
        audit_result = await PreDeployAudit.run(job_id, workspace_path=str(Path.cwd()))
            if not audit_result["passed"]:
                return {
                    "error": "Pre-deploy audit failed",
                    "audit": audit_result,
                    "message": "Fix critical issues before deploying. Use triggered_by=force to bypass.",
                }

        project_token = await DeployService._get_token_for_job(job_id)
        if not project_token:
            return {"error": "No deploy token configured for this project"}

        async with async_session() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return {"error": "Job not found"}

            previous_status = job.status
            job.status = "deploying"
            await session.commit()

            ci_run = CiRun(
                job_id=job_id,
                status="pending",
                ci_provider="easypanel",
            )
            session.add(ci_run)
            await session.commit()

        payload = {
            "service": environment,
            "token": project_token,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.easypanel_endpoint}/api/deploy",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {project_token}",
                        "Content-Type": "application/json",
                    },
                )

                if resp.status_code in (200, 201, 202):
                    async with async_session() as session:
                        result = await session.execute(select(Job).where(Job.id == job_id))
                        job = result.scalar_one_or_none()
                        if job:
                            job.status = "deployed"
                        result2 = await session.execute(
                            select(CiRun).where(
                                CiRun.job_id == job_id,
                                CiRun.ci_provider == "easypanel",
                            ).order_by(CiRun.created_at.desc()).limit(1)
                        )
                        ci = result2.scalar_one_or_none()
                        if ci:
                            ci.status = "passed"
                            ci.finished_at = datetime.now(timezone.utc)
                        await session.commit()

                    from inti.audit import log_action
                    await log_action(
                        actor_type=triggered_by,
                        action="deploy_triggered",
                        job_id=job_id,
                        summary=f"Deploy a {environment} iniciado via Easypanel",
                    )

                    return {
                        "status": "deployed",
                        "environment": environment,
                        "job_id": job_id,
                        "deploy_url": f"{settings.easypanel_endpoint}/deployments/{job_id}",
                    }
                else:
                    async with async_session() as session:
                        result = await session.execute(select(Job).where(Job.id == job_id))
                        job = result.scalar_one_or_none()
                        if job:
                            job.status = previous_status
                        await session.commit()

                    return {
                        "error": "Deploy failed",
                        "status_code": resp.status_code,
                        "detail": resp.text[:500],
                    }

        except httpx.ConnectError:
            async with async_session() as session:
                result = await session.execute(select(Job).where(Job.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = previous_status
                await session.commit()

            return {"error": "Cannot reach Easypanel endpoint"}

    @staticmethod
    async def set_deploy_token(
        project_id: str,
        token: str,
        endpoint: str | None = None,
    ) -> dict:
        async with async_session() as session:
            result = await session.execute(
                select(ProjectKnowledge).where(
                    ProjectKnowledge.project_id == project_id,
                    ProjectKnowledge.key == "easypanel_token",
                )
            )
            entry = result.scalar_one_or_none()

            if entry:
                entry.value = token
            else:
                entry = ProjectKnowledge(
                    project_id=project_id,
                    key="easypanel_token",
                    value=token,
                )
                session.add(entry)

            if endpoint:
                result2 = await session.execute(
                    select(ProjectKnowledge).where(
                        ProjectKnowledge.project_id == project_id,
                        ProjectKnowledge.key == "easypanel_endpoint",
                    )
                )
                ep_entry = result2.scalar_one_or_none()
                if ep_entry:
                    ep_entry.value = endpoint
                else:
                    ep_entry = ProjectKnowledge(
                        project_id=project_id,
                        key="easypanel_endpoint",
                        value=endpoint,
                    )
                    session.add(ep_entry)

            await session.commit()

            from inti.audit import log_action
            await log_action(
                actor_type="human",
                action="deploy_token_set",
                summary=f"Deploy token configurado para proyecto {project_id}",
            )

            return {"status": "ok", "project_id": project_id, "message": "Deploy token stored"}

    @staticmethod
    async def ci_webhook(
        job_id: str,
        status: str,
        provider: str = "github_actions",
        run_id: str | None = None,
        logs_url: str | None = None,
    ) -> dict:
        async with async_session() as session:
            ci_run = CiRun(
                job_id=job_id,
                status=status,
                ci_provider=provider,
                run_id=run_id,
                logs_url=logs_url,
                finished_at=datetime.now(timezone.utc) if status != "pending" else None,
            )
            session.add(ci_run)
            await session.commit()
            await session.refresh(ci_run)

        from inti.events import ci_updated
        event = ci_updated(job_id, status, provider, logs_url)

        if status == "passed":
            await DeployService._try_auto_merge(job_id)

        return {
            "ci_run_id": ci_run.id,
            "status": status,
            "event": event.to_dict(),
        }

    @staticmethod
    async def merge_pr(
        job_id: str,
        merge_method: str = "merge",
        triggered_by: str = "human",
        device_id: str = "",
    ) -> dict:
        if settings.dopa_code_dummy:
            return {"status": "merged", "message": "[DUMMY] PR merged"}

        async with async_session() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return {"error": "Job not found"}

            autonomy_rules = DeployService._get_autonomy_rules(job.autonomy_level)
            if triggered_by == "auto" and not autonomy_rules.get("auto_merge"):
                return {"error": "Auto-merge not allowed for this autonomy level"}

            ci_green = await DeployService._check_ci_green(session, job_id)
            if autonomy_rules.get("requires_ci_green") and not ci_green:
                return {"error": "CI not green. Cannot merge."}

            job.status = "merged"
            await session.commit()

            from inti.audit import log_action
            await log_action(
                actor_type=triggered_by,
                action="merged_pr",
                job_id=job_id,
                device_id=device_id,
                summary=f"PR merged ({merge_method})",
            )

            return {
                "status": "merged",
                "job_id": job_id,
                "merge_method": merge_method,
                "triggered_by": triggered_by,
            }

    @staticmethod
    async def _get_token_for_job(job_id: str) -> str | None:
        async with async_session() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job or not job.repo_id:
                return settings.easypanel_deploy_token

            result2 = await session.execute(
                select(ProjectKnowledge).where(
                    ProjectKnowledge.project_id == job.repo_id,
                    ProjectKnowledge.key == "easypanel_token",
                )
            )
            entry = result2.scalar_one_or_none()
            return entry.value if entry else settings.easypanel_deploy_token

    @staticmethod
    def _get_autonomy_rules(level: str) -> dict:
        from inti.policies import AUTONOMY_RULES
        return AUTONOMY_RULES.get(level, AUTONOMY_RULES.get("human_gatekeeper", {}))

    @staticmethod
    async def _check_ci_green(session, job_id: str) -> bool:
        result = await session.execute(
            select(CiRun)
            .where(CiRun.job_id == job_id)
            .order_by(CiRun.created_at.desc())
            .limit(5)
        )
        runs = result.scalars().all()
        if not runs:
            return False
        return any(r.status == "passed" for r in runs)

    @staticmethod
    async def _try_auto_merge(job_id: str) -> dict | None:
        async with async_session() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return None

            rules = DeployService._get_autonomy_rules(job.autonomy_level)
            if not rules.get("auto_merge"):
                return None

            return await DeployService.merge_pr(
                job_id=job_id,
                triggered_by="auto",
            )

    @staticmethod
    def _dummy_deploy(job_id: str, environment: str) -> dict:
        return {
            "status": "deployed",
            "environment": environment,
            "job_id": job_id,
            "message": "[DUMMY] Deploy simulado a Easypanel",
            "deploy_url": f"https://easypanel.io/dummy/deployments/{job_id}",
        }
