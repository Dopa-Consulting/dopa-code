"""Tests unitarios para AgentLoop — parser de tool calls, guard y tools basicas."""

import pytest
from pathlib import Path


@pytest.fixture
def agent():
    from inti.agent_loop import AgentLoop
    return AgentLoop(workspace=str(Path(__file__).parent.parent))


def test_parse_xml_tool_calls_basic(agent):
    content = '<tool_calls><invoke name="read_file"><parameter name="path">x.py</parameter></invoke></tool_calls>'
    tool_calls, clean = agent._parse_xml_tool_calls(content)
    assert tool_calls is not None
    assert len(tool_calls) == 1
    assert tool_calls[0]["function"]["name"] == "read_file"
    import json
    args = json.loads(tool_calls[0]["function"]["arguments"])
    assert args["path"] == "x.py"
    assert "<tool_calls>" not in clean


def test_parse_xml_tool_calls_namespace(agent):
    content = '<aze:tool_calls><aze:invoke name="list_dir"><aze:parameter name="path" string="true">inti/</aze:parameter></aze:invoke></aze:tool_calls>'
    tool_calls, clean = agent._parse_xml_tool_calls(content)
    assert tool_calls is not None
    assert tool_calls[0]["function"]["name"] == "list_dir"


def test_parse_xml_tool_calls_multiple(agent):
    content = '<tool_calls><invoke name="read_file"><parameter name="path">a.py</parameter></invoke><invoke name="read_file"><parameter name="path">b.py</parameter></invoke></tool_calls>'
    tool_calls, _ = agent._parse_xml_tool_calls(content)
    assert len(tool_calls) == 2


def test_parse_xml_tool_calls_none(agent):
    tool_calls, clean = agent._parse_xml_tool_calls("Hola, como estas?")
    assert tool_calls is None
    assert clean == "Hola, como estas?"


def test_strip_tool_text(agent):
    content = 'Voy a leer el archivo\n{"type": "function", "function": {"name": "read_file", "parameters": {"path": "x"}}}'
    stripped = agent._strip_tool_text(content)
    assert "type" not in stripped
    assert "function" not in stripped


def test_strip_tool_text_json_nested(agent):
    content = 'Texto antes\njson\n{"type": "function", "function": {"name": "list_dir", "parameters": {"path": "."}, "strict": false}}\nTexto despues'
    stripped = agent._strip_tool_text(content)
    assert "strict" not in stripped
    assert "Texto antes" in stripped


@pytest.mark.asyncio
async def test_list_dir_tool(agent):
    from inti.tools import registry, register_builtin_tools
    if not registry.names():
        register_builtin_tools(agent.workspace, agent._resolve_path, agent._check_guardrails)
    result = await registry.execute("list_dir", {"path": "inti"})
    assert "agent_loop.py" in result


@pytest.mark.asyncio
async def test_read_file_tool_dir(agent):
    from inti.tools import registry
    result = await registry.execute("read_file", {"path": "inti"})
    assert "directorio" in result.lower()


@pytest.mark.asyncio
async def test_unknown_tool(agent):
    from inti.tools import registry
    result = await registry.execute("tool_inexistente", {})
    assert "no encontrada" in result
