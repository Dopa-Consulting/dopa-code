"""Tests para AgentLoop — núcleo del agente con tool-calling."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Patch openrouter ANTES de importar agent_loop
import inti.openrouter_client as or_client


@pytest.fixture
def tmp_workspace(tmp_path):
    """Workspace temporal aislado para tests."""
    return str(tmp_path)


@pytest.mark.asyncio
async def test_golden_path_write_file(tmp_workspace):
    """Caso 1: el loop crea un archivo real via monkeypatch de tool_calls."""
    from inti.agent_loop import AgentLoop

    calls = 0

    async def mock_chat(model, messages, tools=None, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "model": model,
                "content": None,
                "finish_reason": "tool_calls",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": '{"path": "notas.md", "content": "- manzana"}',
                        },
                    }
                ],
            }
        else:
            return {
                "model": model,
                "content": "Listo, creé notas.md",
                "finish_reason": "stop",
                "tool_calls": None,
            }

    with patch.object(or_client.openrouter, "chat", side_effect=mock_chat):
        collector = []
        async def emit(event):
            collector.append(event)

        loop = AgentLoop(workspace=tmp_workspace)
        await loop.run("crea notas.md", emit=emit)

    # Verificar archivo creado
    notas = Path(tmp_workspace) / "notas.md"
    assert notas.exists()
    assert notas.read_text() == "- manzana"

    # Verificar eventos
    step_starts = [e for e in collector if e["event_type"] == "step.start"]
    assert len(step_starts) == 1
    assert step_starts[0]["data"]["tool"] == "write_file"

    step_deltas = [e for e in collector if e["event_type"] == "step.delta"]
    assert len(step_deltas) == 1
    assert "write_file" in step_deltas[0]["data"]["text"]

    last = collector[-1]
    assert last["event_type"] == "chat_response"
    assert "Listo" in last["payload"]["content"]


@pytest.mark.asyncio
async def test_run_command_timeout(tmp_workspace):
    """Caso 2: run_command respeta timeout y no cuelga."""
    from inti.agent_loop import AgentLoop

    calls = 0

    async def mock_chat(model, messages, tools=None, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "model": model,
                "content": None,
                "finish_reason": "tool_calls",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "run_command",
                            "arguments": '{"command": "sleep 60"}',
                        },
                    }
                ],
            }
        else:
            return {
                "model": model,
                "content": "Comando ejecutado",
                "finish_reason": "stop",
                "tool_calls": None,
            }

    with patch.object(or_client.openrouter, "chat", side_effect=mock_chat):
        collector = []
        async def emit(event):
            collector.append(event)

        loop = AgentLoop(workspace=tmp_workspace)
        await loop.run("ejecuta sleep 60", emit=emit)

    # El resultado debe contener timeout, no colgar
    step_deltas = [e for e in collector if e["event_type"] == "step.delta"]
    assert len(step_deltas) >= 1
    assert "timeout" in step_deltas[0]["data"]["text"].lower() or "excedió" in step_deltas[0]["data"]["text"]


@pytest.mark.asyncio
async def test_path_escape_rejected(tmp_workspace):
    """Caso 3: ruta que escapa del workspace es rechazada."""
    from inti.agent_loop import AgentLoop

    calls = 0

    async def mock_chat(model, messages, tools=None, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "model": model,
                "content": None,
                "finish_reason": "tool_calls",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "../../etc/passwd"}',
                        },
                    }
                ],
            }
        else:
            return {
                "model": model,
                "content": "No pude leer el archivo",
                "finish_reason": "stop",
                "tool_calls": None,
            }

    with patch.object(or_client.openrouter, "chat", side_effect=mock_chat):
        collector = []
        async def emit(event):
            collector.append(event)

        loop = AgentLoop(workspace=tmp_workspace)
        await loop.run("lee /etc/passwd", emit=emit)

    step_deltas = [e for e in collector if e["event_type"] == "step.delta"]
    assert len(step_deltas) >= 1
    result_text = step_deltas[0]["data"]["text"]
    assert "fuera" in result_text or "escape" in result_text.lower() or "Error" in result_text


def test_resolve_path_rejects_sibling_prefix(tmp_path):
    """El confinamiento usa is_relative_to, no startswith: un directorio hermano
    con prefijo común (ws vs ws-evil) DEBE rechazarse. Este caso pasaba con el
    check viejo por coincidencia de string."""
    from inti.agent_loop import AgentLoop

    ws = tmp_path / "ws"
    ws.mkdir()
    loop = AgentLoop(workspace=str(ws))

    # dentro del workspace: OK
    assert loop._resolve_path("sub/archivo.txt")

    # hermano con prefijo común: DEBE rechazarse
    with pytest.raises(ValueError):
        loop._resolve_path("../ws-evil/secret.txt")

    # escape clásico con ../: DEBE rechazarse
    with pytest.raises(ValueError):
        loop._resolve_path("../../etc/passwd")


@pytest.mark.asyncio
async def test_run_opencode_in_loop(tmp_workspace, monkeypatch):
    """Slice 2 · Caso A: el loop invoca run_opencode via monkeypatch de _run_opencode.
    Verifica que la tool de streaming NO recibe framing duplicado del loop."""
    from inti.agent_loop import AgentLoop
    from inti.agent_loop import _STREAMING_TOOLS

    assert "run_opencode" in _STREAMING_TOOLS

    calls = 0

    async def mock_chat(model, messages, tools=None, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "model": model,
                "content": None,
                "finish_reason": "tool_calls",
                "tool_calls": [
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "run_opencode",
                            "arguments": '{"task": "crea un componente Button"}',
                        },
                    }
                ],
            }
        else:
            return {
                "model": model,
                "content": "Listo, OpenCode generó el componente",
                "finish_reason": "stop",
                "tool_calls": None,
            }

    # Monkeypatch _run_opencode para que emita step.delta y devuelva summary
    original = AgentLoop._run_opencode

    async def mock_run_opencode(self, task, emit):
        await emit({"event_type": "step.start", "data": {"tool": "run_opencode"}})
        await emit({"event_type": "step.delta", "data": {"text": "[OpenCode] creando Button..."}})
        await emit({"event_type": "step.stop", "data": {"index": 0}})
        return "OpenCode terminó. Componente creado."

    monkeypatch.setattr(AgentLoop, "_run_opencode", mock_run_opencode)

    with patch.object(or_client.openrouter, "chat", side_effect=mock_chat):
        collector = []
        async def emit(event):
            collector.append(event)

        loop = AgentLoop(workspace=tmp_workspace)
        await loop.run("usa opencode para crear Button", emit=emit)

    # Verificar que el loop reenvió los eventos de run_opencode
    step_starts = [e for e in collector if e["event_type"] == "step.start"]
    # Debe haber EXACTAMENTE 1 step.start (emitido por _run_opencode, no por el loop)
    assert len(step_starts) == 1, f"Esperaba 1 step.start (de _run_opencode), hay {len(step_starts)}"
    assert step_starts[0]["data"]["tool"] == "run_opencode"

    step_deltas = [e for e in collector if e["event_type"] == "step.delta"]
    assert len(step_deltas) >= 1

    last = collector[-1]
    assert last["event_type"] == "chat_response"
    assert "Listo" in last["payload"]["content"]


@pytest.mark.asyncio
async def test_run_opencode_dummy_mode(tmp_workspace, monkeypatch):
    """Slice 2 · Caso B: _run_opencode en modo dummy devuelve [DUMMY]... sin red."""
    from inti.agent_loop import AgentLoop
    from inti.config import settings

    monkeypatch.setattr(settings, "dopa_code_dummy", True)

    collector = []
    async def emit(event):
        collector.append(event)

    loop = AgentLoop(workspace=tmp_workspace)
    result = await loop._run_opencode("crea un proyecto", emit)

    assert result.startswith("[DUMMY]")
    assert "crea un proyecto" in result

    # Verificar que sí emitió los eventos de framing
    step_starts = [e for e in collector if e["event_type"] == "step.start"]
    assert len(step_starts) == 1

    step_stops = [e for e in collector if e["event_type"] == "step.stop"]
    assert len(step_stops) == 1


# ────────────────────────────────────────── Slice 3 ──────────────────────────

@pytest.mark.asyncio
async def test_gate_blocks_protected_file(tmp_workspace, monkeypatch):
    """Slice 3 · Caso A: gate de guardrails bloquea write_file sobre archivo protegido.
    El archivo NO se escribe. Verificación: step.delta contiene BLOQUEADO + archivo no existe."""
    from inti.agent_loop import AgentLoop
    from inti import guardrails as gr

    # validate_diff real es SÍNCRONO (def, no async) → el mock también debe serlo.
    def mock_validate(project_type, diff_text, files_changed):
        return {
            "passed": False,
            "violations": [
                {"rule_id": "r1", "file": "core.css", "severity": "block", "message": "archivo protegido"}
            ],
        }

    monkeypatch.setattr(gr.guardrail_engine, "validate_diff", mock_validate)

    calls = 0
    async def mock_chat(model, messages, tools=None, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "model": model, "content": None, "finish_reason": "tool_calls",
                "tool_calls": [{
                    "id": "c1", "type": "function",
                    "function": {"name": "write_file", "arguments": '{"path":"core.css","content":"body{color:red}"}'},
                }],
            }
        else:
            return {"model": model, "content": "No pude escribir", "finish_reason": "stop", "tool_calls": None}

    with patch.object(or_client.openrouter, "chat", side_effect=mock_chat):
        collector = []
        async def emit(event): collector.append(event)
        loop = AgentLoop(workspace=tmp_workspace, profile="dopaweb_theme")
        await loop.run("escribe core.css", emit=emit)

    # Verificar que fue bloqueado
    step_deltas = [e for e in collector if e["event_type"] == "step.delta"]
    assert len(step_deltas) == 1
    assert "BLOQUEADO" in step_deltas[0]["data"]["text"]

    # El archivo NO debe existir
    css = Path(tmp_workspace) / "core.css"
    assert not css.exists(), "El archivo protegido NO debe existir"


@pytest.mark.asyncio
async def test_no_profile_no_gate(tmp_workspace):
    """Slice 3 · Caso A2: sin profile, el gate duerme y write_file escribe normal."""
    from inti.agent_loop import AgentLoop

    calls = 0
    async def mock_chat(model, messages, tools=None, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "model": model, "content": None, "finish_reason": "tool_calls",
                "tool_calls": [{
                    "id": "c2", "type": "function",
                    "function": {"name": "write_file", "arguments": '{"path":"readme.md","content":"# Hola"}'},
                }],
            }
        else:
            return {"model": model, "content": "Listo", "finish_reason": "stop", "tool_calls": None}

    with patch.object(or_client.openrouter, "chat", side_effect=mock_chat):
        collector = []
        async def emit(event): collector.append(event)
        loop = AgentLoop(workspace=tmp_workspace)  # sin profile
        await loop.run("escribe readme", emit=emit)

    readme = Path(tmp_workspace) / "readme.md"
    assert readme.exists()
    assert readme.read_text() == "# Hola"


@pytest.mark.asyncio
async def test_recall_memory_dummy(tmp_workspace, monkeypatch):
    """Slice 3 · Caso B: recall_memory tool devuelve contexto en modo dummy."""
    from inti.agent_loop import AgentLoop
    from inti.config import settings

    monkeypatch.setattr(settings, "dopa_code_dummy", True)

    calls = 0
    async def mock_chat(model, messages, tools=None, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "model": model, "content": None, "finish_reason": "tool_calls",
                "tool_calls": [{
                    "id": "c3", "type": "function",
                    "function": {"name": "recall_memory", "arguments": "{}"},
                }],
            }
        else:
            return {"model": model, "content": "Tengo la memoria", "finish_reason": "stop", "tool_calls": None}

    with patch.object(or_client.openrouter, "chat", side_effect=mock_chat):
        collector = []
        async def emit(event): collector.append(event)
        loop = AgentLoop(workspace=tmp_workspace, project_id="p1", profile="dopaweb_theme")
        await loop.run("recuerda", emit=emit)

    step_deltas = [e for e in collector if e["event_type"] == "step.delta"]
    assert len(step_deltas) == 1
    # MemoryContext en dummy mode devuelve "[DUMMY]..." o markdown con skills
    content = step_deltas[0]["data"]["text"]
