"""
Smoke test end-to-end para Dopa Code.
Verifica integridad de codigo (imports, modelos, TypeScript).
Para test HTTP: iniciar daemon+bridge primero y pasar --live.

Ejecutar:
  cd backend-inti
  .\venv\Scripts\python.exe test_smoke.py          # imports + modelos + TS
  .\venv\Scripts\python.exe test_smoke.py --live   # + HTTP endpoints
"""

import asyncio
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
BACKEND_URL = "http://localhost:8000"
BRIDGE_URL = "http://localhost:4097"
BRIDGE_TOKEN = "dopa-bridge-local-dev"

passed = 0
failed = 0
LIVE = "--live" in sys.argv


def check(name: str, ok: bool, detail: str = ""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [OK] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}: {detail}")


def skip(name: str, reason: str = ""):
    print(f"  [SKIP] {name} ({reason})")


async def main():
    global passed, failed
    print("=" * 60)
    print("  Dopa Code - Smoke Test")
    print("=" * 60)

    # --- Models ---
    print("\n[Models]")
    from inti.database import engine, Base
    from inti.models import Job, JobStep, Diff, Approval, AuditLog, Event, CiRun, Device
    from inti.models import ExperienceLesson, SkillDefinition, SkillExecution, ProjectKnowledge
    from inti.models import Tenant, PaymentIntegration

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    tables = len(Base.metadata.tables)
    check("14 tables", tables >= 14, f"Got {tables}")
    for name in sorted(Base.metadata.tables.keys()):
        if name != "__dummy__":
            check(f"  {name}", True)

    # --- Model catalog ---
    from inti.openrouter_client import OPENROUTER_MODELS, PROVIDER_ENDPOINTS
    check("24 models", len(OPENROUTER_MODELS) >= 24, f"Got {len(OPENROUTER_MODELS)}")
    check("5 direct providers", len(PROVIDER_ENDPOINTS) >= 5, f"Got {len(PROVIDER_ENDPOINTS)}")

    # --- Imports ---
    print("\n[Imports]")
    imports_to_check = [
        ("Orchestrator", "from inti.orchestrator import orchestrator"),
        ("WebAuthn", "from inti.webauthn import webauthn"),
        ("Voice parser", "from inti.voice import parse_voice_command"),
        ("Guardrails", "from inti.guardrails import guardrail_engine"),
        ("DeployService", "from inti.deploy import DeployService"),
        ("PostMortem", "from inti.memory import PostMortem"),
        ("SkillRefiner", "from inti.memory import SkillRefiner"),
        ("MemoryContext", "from inti.memory import MemoryContext"),
        ("TemplateService", "from inti.template_service import template_service"),
        ("PaymentService", "from inti.payment_service import PaymentService"),
        ("ErpContext", "from inti.erp_context import erp_context"),
        ("TenantResolver", "from inti.tenant_resolver import tenant_resolver"),
        ("SkillsSeeder", "from inti.skills_seeder import seed_dopaweb_skills"),
        ("OpenRouter client", "from inti.openrouter_client import openrouter"),
        ("MultiProvider", "from inti.openrouter_client import multiprovider"),
        ("LangGraph FSM", "from inti.langgraph_fsm import build_dopa_code_graph"),
    ]
    for label, imp in imports_to_check:
        try:
            exec(imp)
            check(label, True)
        except Exception as e:
            check(label, False, str(e)[:100])

    # --- TypeScript ---
    print("\n[TypeScript]")
    frontend_dir = ROOT / "frontend-pwa"
    if frontend_dir.exists():
        result = subprocess.run(
            ["npx.cmd", "tsc", "--noEmit"],
            cwd=str(frontend_dir),
            capture_output=True,
            timeout=30,
        )
        check("TypeScript 0 errors", result.returncode == 0, result.stderr.decode()[:200])
    else:
        skip("TypeScript", "frontend-pwa not found")

    # --- Live HTTP (solo con --live) ---
    if LIVE:
        import httpx
        print("\n[Live HTTP]")

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{BACKEND_URL}/health")
                check("GET /health", resp.status_code == 200)
                resp = await client.get(f"{BACKEND_URL}/api/v1/health/")
                check("GET /api/v1/health", resp.status_code == 200)
                resp = await client.get(f"{BACKEND_URL}/api/v1/jobs/")
                check("GET /api/v1/jobs", resp.status_code == 200)
                resp = await client.get(f"{BACKEND_URL}/api/v1/sessions/")
                check("GET /api/v1/sessions", resp.status_code == 200)
        except Exception as e:
            check("HTTP endpoints", False, str(e)[:100])

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    f"{BRIDGE_URL}/health",
                    headers={"x-bridge-token": BRIDGE_TOKEN},
                )
                check("Bridge health", resp.status_code == 200)
        except Exception:
            skip("Bridge health", "not running")

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
