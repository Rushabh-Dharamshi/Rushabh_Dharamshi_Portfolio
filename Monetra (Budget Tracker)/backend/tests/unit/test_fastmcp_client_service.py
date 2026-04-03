import datetime as dt
from types import SimpleNamespace

import pytest

from budget_tracker_api.errors import ServiceUnavailableError
from budget_tracker_api.services.fastmcp_client_service import FastMcpClientService


class FakeClientContext:
    def __init__(self, transport, timeout):
        self.transport = transport
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def list_tools(self):
        return [SimpleNamespace(name="tool-a", description="desc", inputSchema={"type": "object"})]

    async def call_tool(self, tool_name, arguments):
        assert tool_name == "tool-a"
        assert arguments == {"amount": 1}
        return SimpleNamespace(data={"ok": True})


def test_fastmcp_client_service_list_tools_and_call_tool(monkeypatch, tmp_path):
    created = {}

    def fake_transport(**kwargs):
        created.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr("budget_tracker_api.services.fastmcp_client_service.StdioTransport", fake_transport)
    monkeypatch.setattr("budget_tracker_api.services.fastmcp_client_service.Client", FakeClientContext)

    service = FastMcpClientService(
        python_executable="python",
        backend_root=tmp_path,
        log_file_path=tmp_path / "logs" / "mcp.log",
    )

    tools = service.list_tools()
    result = service.call_tool("tool-a", {"amount": 1})

    assert tools == [{"name": "tool-a", "description": "desc", "input_schema": {"type": "object"}}]
    assert result == {"ok": True}
    assert created["command"] == "python"
    assert created["args"] == ["-m", "budget_tracker_api.mcp.finance_server"]
    assert created["cwd"] == str(tmp_path)
    assert created["env"]["AUTOMATION_SCHEDULER_ENABLED"] == "false"
    assert (tmp_path / "logs").exists()


def test_fastmcp_client_service_normalise_result_passthrough():
    assert FastMcpClientService._normalise_result({"ok": True}) == {"ok": True}


def test_fastmcp_client_service_wraps_async_failures():
    async def boom():
        raise RuntimeError("boom")

    with pytest.raises(ServiceUnavailableError, match="FastMCP tool call failed"):
        FastMcpClientService._run_async(boom())
