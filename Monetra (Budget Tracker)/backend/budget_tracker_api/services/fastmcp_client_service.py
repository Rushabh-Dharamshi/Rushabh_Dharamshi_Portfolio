from __future__ import annotations

import asyncio
import datetime as dt
import os
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from budget_tracker_api.errors import ServiceUnavailableError


class FastMcpClientService:
    def __init__(
        self,
        *,
        python_executable: str,
        backend_root: str | Path,
        log_file_path: str | Path,
    ):
        self._python_executable = python_executable
        self._backend_root = str(backend_root)
        self._log_file_path = Path(log_file_path)

    def list_tools(self) -> list[dict]:
        async def _runner():
            async with Client(self._build_transport(), timeout=dt.timedelta(seconds=30)) as client:
                tools = await client.list_tools()
                return [self._normalise_tool(tool) for tool in tools]

        return self._run_async(_runner())

    def call_tool(self, tool_name: str, arguments: dict | None = None):
        async def _runner():
            async with Client(self._build_transport(), timeout=dt.timedelta(seconds=60)) as client:
                result = await client.call_tool(tool_name, arguments or {})
                return self._normalise_result(result)

        return self._run_async(_runner())

    def _build_transport(self) -> StdioTransport:
        env = os.environ.copy()
        env["AUTOMATION_SCHEDULER_ENABLED"] = "false"
        self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
        return StdioTransport(
            command=self._python_executable,
            args=["-m", "budget_tracker_api.mcp.finance_server"],
            env=env,
            cwd=self._backend_root,
            keep_alive=False,
            log_file=self._log_file_path,
        )

    @staticmethod
    def _normalise_tool(tool) -> dict:
        return {
            "name": getattr(tool, "name", ""),
            "description": getattr(tool, "description", None),
            "input_schema": getattr(tool, "inputSchema", {}),
        }

    @staticmethod
    def _normalise_result(result):
        if hasattr(result, "data"):
            return result.data
        return result

    @staticmethod
    def _run_async(coroutine):
        try:
            return asyncio.run(coroutine)
        except Exception as exc:
            raise ServiceUnavailableError(f"FastMCP tool call failed: {exc}") from exc
