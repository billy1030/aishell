"""Data models and parsers for Model Context Protocol (MCP) integration."""

import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for a stdio MCP server."""

    name: str
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class MCPTool(BaseModel):
    """Represents a tool exposed by an MCP server."""

    server: str
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)


class MCPToolCall(BaseModel):
    """Represents a parsed MCP tool invocation from an LLM response."""

    server: str
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


_MCP_TAG_RE = re.compile(
    r'<mcp_call\s+server=["\']([^"\']+)["\']\s+tool=["\']([^"\']+)["\']\s*>([\s\S]*?)</mcp_call>',
    re.IGNORECASE,
)


def extract_mcp_call_from_text(text: str) -> Optional[MCPToolCall]:
    """Extract an <mcp_call server="..." tool="...">JSON</mcp_call> block from LLM output."""
    if not text:
        return None
    match = _MCP_TAG_RE.search(text)
    if not match:
        return None
    server, tool, raw_args = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    args: Dict[str, Any] = {}
    if raw_args:
        try:
            parsed = json.loads(raw_args)
            if isinstance(parsed, dict):
                args = parsed
        except json.JSONDecodeError:
            pass
    return MCPToolCall(server=server, tool=tool, arguments=args)

