import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from pydantic import BaseModel

logger = logging.getLogger("MCPClient")

class FinanceMCPClient:
    """Dedicated MCP client communicating with mcp_server via stdio protocol with persistent session."""

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
        self._session: Optional[ClientSession] = None
        self._stdio_cm = None
        self._session_cm = None
        self._lock = asyncio.Lock()
        self._discovered_tools: Optional[List[Dict[str, Any]]] = None

    async def connect(self) -> ClientSession:
        """Establish persistent connection and handshake with MCP server."""
        async with self._lock:
            if self._session is not None:
                return self._session

            self._stdio_cm = stdio_client(self.server_params)
            read, write = await self._stdio_cm.__aenter__()
            self._session_cm = ClientSession(read, write)
            self._session = await self._session_cm.__aenter__()
            await self._session.initialize()
            return self._session

    async def _ensure_connected(self) -> ClientSession:
        if self._session is None:
            return await self.connect()
        return self._session

    async def close(self):
        """Close persistent MCP session and stdio streams."""
        async with self._lock:
            if self._session_cm is not None:
                try:
                    await self._session_cm.__aexit__(None, None, None)
                except Exception:
                    pass
                self._session_cm = None
                self._session = None

            if self._stdio_cm is not None:
                try:
                    await self._stdio_cm.__aexit__(None, None, None)
                except Exception:
                    pass
                self._stdio_cm = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_tools_metadata(self) -> List[Dict[str, Any]]:
        """Connect to MCP server, perform handshake, and discover tool schemas via persistent session."""
        try:
            session = await self._ensure_connected()
            tools_result = await session.list_tools()
            
            tools_list = []
            for tool in tools_result.tools:
                schema = getattr(tool, "inputSchema", None)
                if callable(schema):
                    schema = schema()
                elif schema is None and hasattr(tool, "model_json_schema") and callable(getattr(tool, "model_json_schema")):
                    schema = tool.model_json_schema()
                elif schema is None and hasattr(tool, "schema") and callable(getattr(tool, "schema")):
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
            self._discovered_tools = tools_list
            return tools_list
        except Exception as e:
            logger.error(f"Failed to discover tools from MCP server: {str(e)}")
            await self.close()
            raise RuntimeError(f"MCP Connection/Handshake Error: {str(e)}")

    async def invoke_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool on the MCP server via protocol handshake and call_tool over persistent session."""
        try:
            session = await self._ensure_connected()

            # Verify tool exists
            if self._discovered_tools is None:
                tools_result = await session.list_tools()
                discovered_names = [t.name for t in tools_result.tools]
            else:
                discovered_names = [t["name"] for t in self._discovered_tools]

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
                if err_text.startswith("Error executing tool") or err_text.startswith("Error") or "validation error" in err_text.lower():
                    return {
                        "success": False,
                        "error": "INVALID_ARGUMENT",
                        "message": err_text
                    }
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
            await self.close()
            return {
                "success": False,
                "error": "MCP_FAILURE",
                "message": f"MCP Client/Server error: {str(e)}"
            }
