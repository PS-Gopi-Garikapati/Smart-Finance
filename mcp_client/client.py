import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

logger = logging.getLogger("MCPClient")

class FinanceMCPClient:
    """Dedicated MCP client communicating with mcp_server via stdio protocol."""

    def __init__(self, server_script_path: Optional[str] = None):
        if server_script_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            server_script_path = os.path.join(base_dir, "mcp_server", "server.py")

        self.server_script_path = server_script_path
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_script_path],
            env={**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}
        )

    async def get_tools_metadata(self) -> List[Dict[str, Any]]:
        """Connect to MCP server, perform handshake, and discover tool schemas."""
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    
                    tools_list = []
                    for tool in tools_result.tools:
                        schema = getattr(tool, "inputSchema", None)
                        if callable(schema):
                            schema = schema()
                        elif schema is None and hasattr(tool, "schema") and callable(tool.schema):
                            schema = tool.schema()
                        
                        if isinstance(schema, BaseModel):
                            schema = schema.model_dump()
                        elif not isinstance(schema, dict):
                            schema = {}

                        tools_list.append({
                            "name": tool.name,
                            "description": tool.description or "",
                            "input_schema": schema
                        })
                    return tools_list
        except Exception as e:
            logger.error(f"Failed to discover tools from MCP server: {str(e)}")
            raise RuntimeError(f"MCP Connection/Handshake Error: {str(e)}")

    async def invoke_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool on the MCP server via protocol handshake and call_tool."""
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Verify tool exists
                    tools_result = await session.list_tools()
                    discovered_names = [t.name for t in tools_result.tools]
                    if tool_name not in discovered_names:
                        return {
                            "success": False,
                            "error": "UNKNOWN_TOOL",
                            "message": f"The requested tool '{tool_name}' does not exist on the MCP server."
                        }

                    # Execute tool via MCP protocol
                    result = await session.call_tool(tool_name, arguments=arguments)
                    
                    # Process content returned from MCP server
                    if hasattr(result, "isError") and result.isError:
                        err_text = result.content[0].text if result.content else "Tool execution error"
                        return {
                            "success": False,
                            "error": "TOOL_EXECUTION_ERROR",
                            "message": err_text
                        }

                    if result.content and len(result.content) > 0:
                        first_content = result.content[0]
                        text_val = getattr(first_content, "text", "")
                        
                        if text_val.startswith("Error executing tool") or text_val.startswith("Error"):
                            return {
                                "success": False,
                                "error": "INVALID_ARGUMENT",
                                "message": text_val
                            }
                        
                        try:
                            parsed = json.loads(text_val)
                            return parsed
                        except json.JSONDecodeError:
                            return {"success": True, "raw_result": text_val}
                    
                    return {"success": True, "result": "No content returned"}

        except Exception as e:
            logger.error(f"MCP client invocation failure: {str(e)}")
            return {
                "success": False,
                "error": "MCP_FAILURE",
                "message": f"MCP Client/Server error: {str(e)}"
            }
