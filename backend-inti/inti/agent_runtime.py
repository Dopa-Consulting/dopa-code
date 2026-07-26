import json
import subprocess
import httpx
from pathlib import Path

from inti.config import settings

BRIDGE_URL = "http://localhost:4097"
BRIDGE_TOKEN = "dopa-bridge-local-dev"


class AgentRuntime:
    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.dummy_mode = settings.dopa_code_dummy
        self.opencode_path = self._resolve_opencode_path()
        self._bridge_process = None

    def _resolve_opencode_path(self) -> Path:
        agent_runtime_dir = Path(__file__).parent.parent.parent / "agent-runtime"
        opencode_dir = agent_runtime_dir / "opencode"
        if opencode_dir.exists():
            return opencode_dir
        return agent_runtime_dir

    async def start_bridge(self) -> dict:
        if self.dummy_mode:
            return {"status": "dummy", "message": "Bridge no iniciado en modo dummy"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{BRIDGE_URL}/health",
                    headers={"x-bridge-token": BRIDGE_TOKEN},
                    timeout=3.0,
                )
                if resp.status_code == 200:
                    return {"status": "running", **resp.json()}

            bridge_dir = Path(__file__).parent.parent.parent / "agent-runtime"
            self._bridge_process = subprocess.Popen(
                ["bun", "bridge.js"],
                cwd=str(bridge_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return {"status": "started", "bridge_url": BRIDGE_URL}
        except httpx.ConnectError:
            return {"status": "unreachable", "message": "Bridge no responde"}

    def stop_bridge(self):
        if self._bridge_process:
            self._bridge_process.terminate()
            self._bridge_process = None

    async def _update_job_status(self, job_id: str, status: str) -> None:
        try:
            from inti.database import async_session
            from inti.models.job import Job
            from sqlalchemy import select

            async with async_session() as session:
                result = await session.execute(select(Job).where(Job.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = status
                    await session.commit()
        except Exception:
            pass

    async def _inject_erp_context(self, job_id: str, prompt: str) -> str:
        try:
            from inti.database import async_session
            from inti.models.job import Job
            from sqlalchemy import select

            async with async_session() as session:
                result = await session.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()

            context_parts = []

            if job and job.tenant_id:
                from inti.erp_context import erp_context
                erp_ctx = await erp_context.build_prompt_context(job.tenant_id)
                context_parts.append(erp_ctx)

            if job:
                from inti.guardrails import guardrail_engine
                guardrail_prompt = guardrail_engine.build_system_prompt(
                    job.profile if job.profile in ("dopaweb_theme", "dopaweb_payment") else "dopaweb_theme"
                )
                if guardrail_prompt:
                    context_parts.append(guardrail_prompt)

                from inti.memory import MemoryContext
                memory_ctx = await MemoryContext.get_context_for_job(
                    job.repo_id, job.profile
                )
                if memory_ctx and "[DUMMY]" not in memory_ctx:
                    context_parts.append(memory_ctx)

            context = "\n\n".join(context_parts) if context_parts else ""
            return f"{context}\n\n## Tarea\n\n{prompt}" if context else prompt
        except Exception:
            return prompt

    # --- Discovery Mode (The Architect pattern) ---

    def start_discovery(self, job_id: str, idea: str) -> dict:
        """Fase 1: Descubrimiento. El agente hace preguntas, no ejecuta codigo."""
        self._audit("llm_architect", "discovery_started", job_id, f"Idea: {idea[:200]}")

        archetype = self._detect_archetype(idea)

        questions = [
            {
                "id": "q1",
                "question": f"Veo que es un proyecto tipo **{archetype}**. Cuentame mas: que problema resuelve y para quien?",
                "type": "open",
            },
            {
                "id": "q2",
                "question": "Que tan grande debe ser la primera version? MVP minimo o producto completo?",
                "type": "choice",
                "options": ["MVP (minimo viable, 1-2 semanas)", "Producto base (1 mes)", "Completo (3+ meses)"],
            },
            {
                "id": "q3",
                "question": "Ya tenes algo de esto? (codigo existente, diseño, base de datos, dominio?)",
                "type": "open",
            },
        ]

        return {
            "phase": "discovery",
            "job_id": job_id,
            "archetype": archetype,
            "questions": questions,
            "message": "Responde estas preguntas para empezar a diseñar tu proyecto.",
        }

    def continue_discovery(
        self, job_id: str, answers: dict, previous_phase: str = "discovery"
    ) -> dict:
        """Fase 2: Deep dive. Preguntas especificas segun arquetipo y respuestas anteriores."""
        self._audit("llm_architect", "discovery_continued", job_id, f"Answers: {len(answers)}")

        archetype = self._detect_archetype(str(answers))

        if previous_phase == "discovery":
            questions = [
                {
                    "id": "dd1",
                    "question": "Necesitas cuentas de usuario? Que roles? (admin, cliente, staff...)",
                    "type": "open",
                },
                {
                    "id": "dd2",
                    "question": "El proyecto necesita procesar pagos? Que metodos?",
                    "type": "choice",
                    "options": ["No necesita pagos", "MercadoPago", "Stripe", "PayPal", "Otro / Multiples"],
                },
                {
                    "id": "dd3",
                    "question": "Necesitas funciones en tiempo real? (notificaciones, chat, dashboard en vivo)",
                    "type": "choice",
                    "options": ["No", "Notificaciones basicas", "Chat en tiempo real", "Dashboard en vivo"],
                },
            ]
        elif previous_phase == "deep_dive":
            questions = [
                {
                    "id": "ac1",
                    "question": f"Para el proyecto tipo **{archetype}**, te propongo:\n\n"
                    f"**Frontend**: Next.js + React + Tailwind\n"
                    f"**Backend**: Express + Sequelize + PostgreSQL (si es parte de Dopa)\n"
                    f"**Auth**: JWT + WebAuthn\n"
                    f"**Hosting**: Easypanel via Dopa Code\n\n"
                    "Te parece este stack? Queres cambiar algo?",
                    "type": "open",
                },
            ]
        else:
            questions = []

        return {
            "phase": "deep_dive" if previous_phase == "discovery" else "architecture",
            "job_id": job_id,
            "archetype": archetype,
            "questions": questions,
            "message": "Respondiendo estas preguntas defino la arquitectura completa.",
        }

    def finalize_discovery(
        self, job_id: str, answers: dict, archetype: str = "saas-webapp"
    ) -> dict:
        """Fase 4: Generar blueprint. Produce las 16 secciones."""
        self._audit("llm_architect", "blueprint_generated", job_id, f"Archetype: {archetype}")

        return {
            "phase": "blueprint_ready",
            "job_id": job_id,
            "archetype": archetype,
            "blueprint": {
                "title": f"Blueprint: {answers.get('q1', 'Nuevo Proyecto')[:50]}",
                "sections": [
                    {"id": 1, "name": "Project Overview", "status": "ready"},
                    {"id": 2, "name": "Tech Stack", "status": "ready"},
                    {"id": 3, "name": "Directory Structure", "status": "ready"},
                    {"id": 4, "name": "Data Model", "status": "pending"},
                    {"id": 5, "name": "API Design", "status": "pending"},
                    {"id": 6, "name": "Frontend Architecture", "status": "pending"},
                    {"id": 7, "name": "Design System", "status": "pending"},
                    {"id": 8, "name": "Auth & Authorization", "status": "pending"},
                    {"id": 9, "name": "Build Order", "status": "ready"},
                    {"id": 10, "name": "Environment Setup", "status": "ready"},
                    {"id": 11, "name": "Dependencies", "status": "pending"},
                    {"id": 12, "name": "Deployment", "status": "ready"},
                    {"id": 13, "name": "Testing", "status": "pending"},
                    {"id": 14, "name": "Skills to Use", "status": "ready"},
                    {"id": 15, "name": "AGENTS.md", "status": "pending"},
                    {"id": 16, "name": "Rules", "status": "ready"},
                ],
            },
            "next_action": "El blueprint esta listo para ser ejecutado por Inti + OpenCode.",
        }

    def _detect_archetype(self, idea: str) -> str:
        idea_lower = idea.lower()
        if any(w in idea_lower for w in ["saas", "app web", "dashboard", "admin", "panel"]):
            return "saas-webapp"
        if any(w in idea_lower for w in ["api", "backend", "microservicio", "endpoint"]):
            return "api-backend"
        if any(w in idea_lower for w in ["landing", "portfolio", "sitio", "marketing", "pagina"]):
            return "marketing-site"
        if any(w in idea_lower for w in ["movil", "app", "ios", "android", "expo"]):
            return "mobile-app"
        if any(w in idea_lower for w in ["tienda", "ecommerce", "comercio", "dopaweb"]):
            return "dopaweb-saas"
        if any(w in idea_lower for w in ["blog", "contenido", "cms", "docs"]):
            return "content-platform"
        return "saas-webapp"

    # --- Plan/Execute ---

    async def plan_change(self, job_id: str, prompt: str) -> dict:
        self._audit("llm_architect", "plan_requested", job_id, f"Prompt: {prompt[:200]}")
        await self._update_job_status(job_id, "executing")
        enhanced_prompt = await self._inject_erp_context(job_id, prompt)
        if self.dummy_mode:
            return {
                "plan": f"[DUMMY] Plan simulado para job {job_id}",
                "steps": ["analizar", "modificar", "testear"],
                "estimated_files": 3,
                "model": settings.architect_model,
            }
        return await self._call_bridge("POST", "/plan", {
            "title": f"Inti Plan {job_id[:8]}",
            "prompt": enhanced_prompt,
            "directory": str(self.workspace_root),
            "agent": "plan",
        })

    async def apply_change(self, job_id: str, plan: dict, branch_name: str) -> dict:
        self._audit("llm_executor", "execution_started", job_id, f"Branch: {branch_name}")
        if self.dummy_mode:
            return {
                "success": True,
                "branch": branch_name,
                "files_modified": ["dummy/file_a.py", "dummy/file_b.py"],
                "model": settings.executor_model,
            }
        return await self._call_bridge("POST", "/execute", {
            "title": f"Inti Execute {job_id[:8]}",
            "prompt": json.dumps(plan),
            "directory": str(self.workspace_root),
            "agent": "build",
        })

    async def generate_diff(self, job_id: str, branch_name: str) -> dict:
        self._audit("llm_executor", "diff_generated", job_id, f"Diff from {branch_name}")
        if self.dummy_mode:
            return {
                "summary": f"[DUMMY] Diff simulado",
                "diff_text": (
                    "diff --git a/dummy/file_a.py b/dummy/file_a.py\n"
                    "--- a/dummy/file_a.py\n"
                    "+++ b/dummy/file_a.py\n"
                    "@@ -1,5 +1,7 @@\n"
                    " # Dummy file A\n"
                    ' def hello() -> str:\n'
                    '-    return "hello"\n'
                    '+    return "hello from Dopa Code"\n'
                ),
                "files_changed": ["dummy/file_a.py", "dummy/file_b.py"],
            }
        return await self._call_bridge("GET", f"/diff?directory={self.workspace_root}", None)

    async def run_tests(self, job_id: str) -> dict:
        self._audit("llm_executor", "tests_started", job_id, "Running test suite")
        if self.dummy_mode:
            return {"passed": True, "total": 12, "failed": 0, "errors": 0, "time_seconds": 3.2}
        return await self._call_bridge("POST", "/execute", {
            "title": f"Inti Tests {job_id[:8]}",
            "prompt": "Run the test suite and report results",
            "directory": str(self.workspace_root),
            "agent": "build",
        })

    async def run_qa_review(self, job_id: str, diff_text: str) -> dict:
        self._audit("llm_qa", "qa_review_started", job_id, "Reviewing diff")

        guardrail_result = await self._validate_guardrails(job_id, diff_text, [])
        if not guardrail_result.get("passed", True):
            return {
                "passed": False,
                "score": 0.0,
                "issues": guardrail_result.get("violations", []),
                "blocked_by_guardrails": True,
                "message": "Diff bloqueado por guardrails. Archivos protegidos modificados.",
            }

        if self.dummy_mode:
            return {"passed": True, "score": 0.92, "issues": [], "model": settings.qa_model}
        return await self._call_bridge("POST", "/execute", {
            "title": f"Inti QA {job_id[:8]}",
            "prompt": f"Review the following diff for issues:\n{diff_text[:3000]}",
            "directory": str(self.workspace_root),
            "agent": "review",
        })

    async def _call_bridge(self, method: str, path: str, body: dict | None) -> dict:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {"x-bridge-token": BRIDGE_TOKEN, "Content-Type": "application/json"}
                if method == "GET":
                    resp = await client.get(f"{BRIDGE_URL}{path}", headers=headers)
                elif method == "POST":
                    resp = await client.post(
                        f"{BRIDGE_URL}{path}",
                        headers=headers,
                        json=body if body else {},
                    )
                else:
                    return {"error": f"Unsupported method: {method}"}

                if resp.status_code >= 400:
                    return {"error": f"Bridge error {resp.status_code}", "detail": resp.text[:500]}
                return resp.json() if resp.text else {"status": "ok"}
        except httpx.ConnectError:
            return {"error": "Bridge unreachable", "url": f"{BRIDGE_URL}{path}"}
        except httpx.TimeoutException:
            return {"error": "Bridge timeout", "url": f"{BRIDGE_URL}{path}"}

    def _audit(self, actor_type: str, action: str, job_id: str, summary: str) -> None:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._audit_async(actor_type, action, job_id, summary))
        except RuntimeError:
            pass

    async def _audit_async(self, actor_type: str, action: str, job_id: str, summary: str) -> None:
        from inti.audit import log_action
        await log_action(
            actor_type=actor_type,
            action=action,
            job_id=job_id,
            summary=summary,
        )

    async def _validate_guardrails(
        self, job_id: str, diff_text: str, files_changed: list[str]
    ) -> dict:
        try:
            from inti.database import async_session
            from inti.models.job import Job
            from sqlalchemy import select
            from inti.guardrails import guardrail_engine

            async with async_session() as session:
                result = await session.execute(
                    select(Job).where(Job.id == job_id)
                )
                job = result.scalar_one_or_none()

            if not job:
                return {"passed": True}

            project_type = job.profile
            if project_type not in ("dopaweb_theme", "dopaweb_payment"):
                return {"passed": True}

            if not files_changed and diff_text:
                files_changed = [
                    line[6:] for line in diff_text.split("\n")
                    if line.startswith("--- a/") or line.startswith("+++ b/")
                ]
                files_changed = list(set(
                    f.split("\t")[0] for f in files_changed
                ))

            return guardrail_engine.validate_diff(project_type, diff_text, files_changed)
        except Exception as e:
            logger = __import__("logging").getLogger("inti.agent_runtime")
            logger.warning(f"Guardrail validation failed: {e}")
            return {"passed": True, "warning": str(e)}

    # --- Gemini Interactions API routing ---

    async def _route_chat(self, job_id: str, role: str, prompt: str, model_override: str | None = None) -> dict:
        """
        Rutea una llamada de chat al mejor proveedor segun el modelo configurado.
        Prioridad: Gemini Interactions > OpenRouter > Direct APIs > Bridge (fallback).

        Si el modelo es de Google y la API key esta configurada, usa Interactions API
        (cache implicito, background execution, menor costo).
        """
        from inti.database import async_session
        from inti.models.job import Job
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()

        model = model_override or (
            settings.architect_model if role == "architect" else
            settings.executor_model if role == "executor" else
            settings.qa_model
        )

        # Gemini Interactions API (nuevo endpoint unificado)
        if "gemini" in model or "google" in model:
            from inti.gemini_interactions import gemini_interactions

            if gemini_interactions.is_configured:
                gemini_model = model.split("/")[-1] if "/" in model else model

                system = None
                if role == "architect":
                    system = "You are an Architect LLM. Design complete software blueprints. Ask clarifying questions before proposing solutions."
                elif role == "executor":
                    system = "You are an Executor LLM. Write production-quality code. Follow the plan precisely."
                elif role == "qa":
                    system = "You are a QA Reviewer LLM. Find bugs, security issues, and improvements. Be thorough."

                result = await gemini_interactions.interact(
                    model=gemini_model,
                    user_input=prompt,
                    system_instruction=system,
                    background=len(prompt) > 5000,  # background para prompts largos
                )
                if "output" in result:
                    return {"content": result["output"], "model": gemini_model, "interaction_id": result.get("interaction_id")}
                if "error" in result:
                    logger.info(f"Gemini Interactions failed: {result['error']}, falling back to bridge")

        # Deep Research agent para investigacion
        if role == "architect" and model in ("deep-research", "deep-research-max", "research"):
            from inti.gemini_interactions import gemini_interactions

            if gemini_interactions.is_configured:
                max_mode = "max" in model
                result = await gemini_interactions.deep_research(prompt, max_mode)
                if "output" in result:
                    return {"content": result["output"], "model": "deep-research", "interaction_id": result.get("interaction_id")}

        # Antigravity Agent nativo para QA
        if role == "qa" and model in ("antigravity", "antigravity-agent"):
            from inti.gemini_interactions import gemini_interactions

            if gemini_interactions.is_configured:
                code_context = ""
                if job:
                    code_context = f"Job: {job.title} (profile: {job.profile})"
                result = await gemini_interactions.antigravity_qa(prompt, code_context)
                if "output" in result:
                    return {"content": result["output"], "model": "antigravity-agent", "interaction_id": result.get("interaction_id")}

        # Fallback al bridge (OpenCode CLI)
        return await self._call_bridge("POST", "/execute", {
            "title": f"Inti {role.title()} {job_id[:8]}",
            "prompt": prompt,
            "directory": str(self.workspace_root),
            "agent": role,
        })

    async def research_for_architect(self, job_id: str, topic: str) -> dict:
        """Usa Deep Research para investigar un tema antes de diseñar."""
        self._audit("llm_architect", "research_started", job_id, f"Researching: {topic}")
        result = await self._route_chat(job_id, "architect", topic, "deep-research-max")
        return {"research_result": result, "topic": topic}

    async def qa_with_antigravity_native(self, job_id: str, code: str) -> dict:
        """Usa Antigravity Agent nativo para QA."""
        self._audit("llm_qa", "qa_antigravity", job_id, "QA with Antigravity Agent")
        return await self._route_chat(job_id, "qa", code, "antigravity-agent")


agent_runtime = AgentRuntime()
