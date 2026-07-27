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
