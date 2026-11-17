"""Lightweight JSON-RPC 2.0 stdio MCP client and server manager."""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from aishell.config.settings import get_default_config_dir
from aishell.mcp.schema import MCPServerConfig, MCPTool


class MCPStdioClient:
    """Minimal async JSON-RPC 2.0 client for a stdio MCP server."""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._req_id = 0

    async def connect(self) -> None:
        """Spawn the MCP server subprocess and perform the initialize handshake."""
        if self._proc is not None and self._proc.returncode is None:
            return

        env = os.environ.copy()
        env.update(self.config.env)

        self._proc = await asyncio.create_subprocess_exec(
            self.config.command,
            *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
        )

        await self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "aishell", "version": "0.1.2"},
            },
        )
        await self._notify("notifications/initialized", {})

    async def _notify(self, method: str, params: Dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            return
        payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params}) + "\n"
        self._proc.stdin.write(payload.encode("utf-8"))
        await self._proc.stdin.drain()

    async def _request(self, method: str, params: Dict[str, Any], timeout: float = 15.0) -> Any:
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            raise RuntimeError(f"MCP server '{self.config.name}' is not running.")

        self._req_id += 1
        req_id = self._req_id
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        ) + "\n"
        self._proc.stdin.write(payload.encode("utf-8"))
        await self._proc.stdin.drain()

        async def _read_response() -> Any:
            assert self._proc and self._proc.stdout
            while True:
                line = await self._proc.stdout.readline()
                if not line:
                    raise RuntimeError(f"MCP server '{self.config.name}' closed stdout unexpectedly.")
                try:
                    msg = json.loads(line.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    continue
                if msg.get("id") == req_id:
                    if "error" in msg:
                        err = msg["error"]
                        raise RuntimeError(f"MCP error ({err.get('code')}): {err.get('message')}")
                    return msg.get("result", {})

        return await asyncio.wait_for(_read_response(), timeout=timeout)

    async def list_tools(self) -> List[MCPTool]:
        """Query tools/list from the connected MCP server."""
        await self.connect()
        result = await self._request("tools/list", {})
        tools: List[MCPTool] = []
        for item in result.get("tools", []):
            tools.append(
                MCPTool(
                    server=self.config.name,
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    input_schema=item.get("inputSchema", {}),
                )
            )
        return tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Invoke tools/call and return flattened text output."""
        await self.connect()
        result = await self._request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            timeout=30.0,
        )
        parts: List[str] = []
        for block in result.get("content", []):
            if isinstance(block, dict):
                if "text" in block:
                    parts.append(str(block["text"]))
                else:
                    parts.append(json.dumps(block))
            else:
                parts.append(str(block))
        return "\n".join(parts) if parts else json.dumps(result)

    async def close(self) -> None:
        """Terminate the MCP server subprocess."""
        if self._proc and self._proc.returncode is None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=2.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None


class MCPManager:
    """Discovers ~/.config/aishell/mcp.json servers, caches tools, and executes tool calls."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or (get_default_config_dir() / "mcp.json")
        self.servers: Dict[str, MCPServerConfig] = {}
        self.clients: Dict[str, MCPStdioClient] = {}
        self.tools: List[MCPTool] = []
        self.reload_config()

    def reload_config(self) -> None:
        """Load MCP server definitions from mcp.json."""
        self.servers = {}
        if not self.config_path.is_file():
            return
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            raw_servers = data.get("mcpServers", {})
            if isinstance(raw_servers, dict):
                for name, cfg in raw_servers.items():
                    if isinstance(cfg, dict) and cfg.get("command"):
                        self.servers[name] = MCPServerConfig(
                            name=name,
                            command=cfg["command"],
                            args=list(cfg.get("args", [])),
                            env=dict(cfg.get("env", {})),
                            enabled=bool(cfg.get("enabled", True)),
                        )
        except Exception:
            pass

    async def discover_tools(self) -> List[MCPTool]:
        """Connect to enabled MCP servers and refresh the tool catalog."""
        discovered: List[MCPTool] = []
        for name, cfg in self.servers.items():
            if not cfg.enabled:
                continue
            client = self.clients.get(name) or MCPStdioClient(cfg)
            self.clients[name] = client
            try:
                discovered.extend(await client.list_tools())
            except Exception:
                continue
        self.tools = discovered
        return discovered

    async def call_tool(self, server: str, tool: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool on the named MCP server."""
        cfg = self.servers.get(server)
        if not cfg or not cfg.enabled:
            raise ValueError(f"MCP server '{server}' is not configured or disabled.")
        client = self.clients.get(server) or MCPStdioClient(cfg)
        self.clients[server] = client
        return await client.call_tool(tool, arguments)

    async def close_all(self) -> None:
        """Shut down all active MCP server subprocesses."""
        for client in self.clients.values():
            await client.close()
        self.clients.clear()

    def format_mcp_context(self) -> str:
        """Format discovered MCP tools into XML instructions for the LLM."""
        if not self.tools:
            return ""
        lines = [
            "You also have access to the following MCP tools. "
            'To invoke one, output: <mcp_call server="SERVER" tool="TOOL">{"arg": "value"}</mcp_call>',
            "<mcp_tools>",
        ]
        for t in self.tools:
            desc = t.description.replace("\n", " ")[:160]
            lines.append(f'  <tool server="{t.server}" name="{t.name}">{desc}</tool>')
        lines.append("</mcp_tools>")
        return "\n".join(lines)

