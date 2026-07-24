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

    async def plan_change(self, job_id: str, prompt: str) -> dict:
        self._audit("llm_architect", "plan_requested", job_id, f"Prompt: {prompt[:200]}")
        if self.dummy_mode:
            return {
                "plan": f"[DUMMY] Plan simulado para job {job_id}",
                "steps": ["analizar", "modificar", "testear"],
                "estimated_files": 3,
                "model": settings.architect_model,
            }
        return await self._call_bridge("POST", "/plan", {
            "title": f"Inti Plan {job_id[:8]}",
            "prompt": prompt,
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
        from inti.audit import log_action

        log_action(
            actor_type=actor_type,
            action=action,
            job_id=job_id,
            summary=summary,
        )


agent_runtime = AgentRuntime()
