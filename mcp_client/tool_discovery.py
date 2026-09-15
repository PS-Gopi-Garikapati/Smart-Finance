from typing import List, Dict, Any
from mcp_client.client import FinanceMCPClient

class ToolDiscoverer:
    """Discovers tools via FinanceMCPClient and formats schemas for LLM Policy Layer."""

    def __init__(self, client: FinanceMCPClient):
        self.client = client
        self.cached_tools: List[Dict[str, Any]] = []

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Query MCP Server and return clean list of available tools."""
        self.cached_tools = await self.client.get_tools_metadata()
        return self.cached_tools

    def format_tools_for_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """Format discovered tool definitions into clear text for LLM policy instructions."""
        formatted_list = []
        for index, tool in enumerate(tools, 1):
            name = tool.get("name")
            desc = tool.get("description")
            schema = tool.get("input_schema", {})
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            param_str = ", ".join([
                f"{k}: {v.get('type', 'any')}{' (required)' if k in required else ''}"
                for k, v in properties.items()
            ])

            formatted_list.append(
                f"{index}. Tool: `{name}`\n"
                f"   Description: {desc}\n"
                f"   Parameters: ({param_str})"
            )

        return "\n\n".join(formatted_list)
