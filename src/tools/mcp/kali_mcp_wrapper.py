"""
MCP Protocol Wrapper for Kali Tools Flask Server
This wraps the custom REST API at http://192.168.1.135:5000 to speak MCP protocol
"""

import asyncio
import json
import requests
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

KALI_SERVER_URL = "http://192.168.1.135:5000"

app = Server("kali_tools")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Kali tools from the REST API"""
    try:
        response = requests.get(f"{KALI_SERVER_URL}/mcp/capabilities", timeout=5)
        response.raise_for_status()
        capabilities = response.json()
        
        tools = []
        for tool_def in capabilities.get("tools", []):
            tools.append(Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                inputSchema=tool_def.get("input_schema", {})
            ))
        
        return tools
    except Exception as e:
        print(f"Error loading tools: {e}")
        return []


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Execute a Kali tool via the REST API"""
    try:
        response = requests.get(f"{KALI_SERVER_URL}/mcp/capabilities", timeout=5)
        response.raise_for_status()
        capabilities = response.json()
        
        tool_endpoint = None
        for tool_def in capabilities.get("tools", []):
            if tool_def["name"] == name:
                tool_endpoint = tool_def["execution_endpoint"]
                break
        
        if not tool_endpoint:
            return [TextContent(
                type="text",
                text=f"Error: Tool '{name}' not found"
            )]
        
        full_url = f"{KALI_SERVER_URL}{tool_endpoint}"
        payload = {"arguments": arguments}
        
        response = requests.post(full_url, json=payload, timeout=1800)
        response.raise_for_status()
        result = response.json()
        
        if "output" in result:
            output_data = result["output"]
            if isinstance(output_data, dict):
                stdout = output_data.get("stdout", "")
                stderr = output_data.get("stderr", "")
                return_code = output_data.get("return_code", -1)
                timed_out = output_data.get("timed_out", False)
                
                output_text = ""
                if timed_out:
                    output_text = f"⚠️ Command timed out after 1800s\n\nPartial output:\n{stdout}"
                elif return_code != 0:
                    output_text = f"Command exited with code {return_code}\n\n"
                    if stdout:
                        output_text += f"Output:\n{stdout}"
                    if stderr and stderr.strip():
                        output_text += f"\n\nErrors/Warnings:\n{stderr}"
                else:
                    if stdout:
                        output_text = f"Output:\n{stdout}"
                    if stderr and stderr.strip():
                        output_text += f"\n\nErrors/Warnings:\n{stderr}"
                
                return [TextContent(
                    type="text",
                    text=output_text or "Command completed with no output"
                )]
            else:
                return [TextContent(type="text", text=str(output_data))]
        else:
            return [TextContent(type="text", text=str(result))]
            
    except requests.exceptions.Timeout:
        return [TextContent(
            type="text",
            text="Error: Tool execution timed out after 1800s"
        )]
    except requests.exceptions.RequestException as e:
        return [TextContent(
            type="text",
            text=f"Error: Tool execution failed: {str(e)}"
        )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: Unexpected error: {str(e)}"
        )]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
