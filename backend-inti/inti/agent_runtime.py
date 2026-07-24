import json
import subprocess
from pathlib import Path

from inti.config import settings


class AgentRuntime:
    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.dummy_mode = settings.dopa_code_dummy
        self.opencode_path = self._resolve_opencode_path()

    def _resolve_opencode_path(self) -> Path:
        agent_runtime_dir = Path(__file__).parent.parent.parent / "agent-runtime"
        opencode_dir = agent_runtime_dir / "opencode"
        if opencode_dir.exists():
            return opencode_dir
        return agent_runtime_dir

    def plan_change(self, job_id: str, prompt: str) -> dict:
        self._audit("llm_architect", "plan_requested", job_id, f"Prompt: {prompt[:200]}")
        if self.dummy_mode:
            return {
                "plan": f"[DUMMY] Plan simulado para job {job_id}",
                "steps": ["analizar", "modificar", "testear"],
                "estimated_files": 3,
                "model": settings.architect_model,
            }
        return self._run_opencode("plan", job_id, prompt)

    def apply_change(self, job_id: str, plan: dict, branch_name: str) -> dict:
        self._audit("llm_executor", "execution_started", job_id, f"Branch: {branch_name}")
        if self.dummy_mode:
            return {
                "success": True,
                "branch": branch_name,
                "files_modified": ["dummy/file_a.py", "dummy/file_b.py"],
                "model": settings.executor_model,
            }
        return self._run_opencode("apply", job_id, json.dumps(plan))

    def generate_diff(self, job_id: str, branch_name: str) -> dict:
        self._audit("llm_executor", "diff_generated", job_id, f"Diff from {branch_name}")
        if self.dummy_mode:
            return {
                "summary": f"[DUMMY] Diff simulado - cambios en 2 archivos",
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
        return self._run_opencode("diff", job_id, branch_name)

    def run_tests(self, job_id: str) -> dict:
        self._audit("llm_executor", "tests_started", job_id, "Running test suite")
        if self.dummy_mode:
            return {"passed": True, "total": 12, "failed": 0, "errors": 0, "time_seconds": 3.2}
        return self._run_opencode("test", job_id, "")

    def run_qa_review(self, job_id: str, diff_text: str) -> dict:
        self._audit("llm_qa", "qa_review_started", job_id, "Reviewing diff")
        if self.dummy_mode:
            return {"passed": True, "score": 0.92, "issues": [], "model": settings.qa_model}
        return self._run_opencode("qa", job_id, diff_text)

    def _run_opencode(self, command: str, job_id: str, payload: str) -> dict:
        return {
            "status": "not_implemented",
            "command": command,
            "job_id": job_id,
            "message": "OpenCode CLI integration pending (Fase 3)",
        }

    def _audit(self, actor_type: str, action: str, job_id: str, summary: str) -> None:
        from inti.audit import log_action

        log_action(
            actor_type=actor_type,
            action=action,
            job_id=job_id,
            summary=summary,
        )


agent_runtime = AgentRuntime()
