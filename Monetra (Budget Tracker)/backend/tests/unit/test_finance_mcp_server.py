import pytest

from budget_tracker_api.errors import ValidationError
from budget_tracker_api.services.finance_mcp_server import FinanceMcpServer


def test_finance_mcp_server_lists_tools_and_calls_handlers():
    server = FinanceMcpServer({
        "get_dashboard_summary": lambda arguments: {"arguments": arguments},
    })

    tools = server.list_tools()
    result = server.call_tool("get_dashboard_summary", {"limit": 5})

    assert any(tool["name"] == "retrieve_finance_context" for tool in tools)
    assert any(tool["name"] == "send_month_end_email_now" for tool in tools)
    assert result == {"arguments": {"limit": 5}}


def test_finance_mcp_server_raises_for_unknown_tools():
    server = FinanceMcpServer({})

    with pytest.raises(ValidationError, match="Unknown MCP tool"):
        server.call_tool("missing")
