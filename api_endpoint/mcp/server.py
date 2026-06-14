import base64
import io
import json
from typing import Any
import logging
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent, ToolResult
import mcp.types as types

log = logging.getLogger("mcp")

def mount_mcp(app) -> Server:
    """Mount MCP server with floorplan tools"""
    server = Server("magicplan-floorplan")
    
    # Register tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="generate_floorplan_from_base64",
                description="Generate a 2D CAD floorplan from a 360-degree panorama image. Returns PNG, DXF, and debug visualizations.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_base64": {
                            "type": "string",
                            "description": "Base64-encoded image data of a 360-degree panorama (JPEG or PNG)",
                        }
                    },
                    "required": ["image_base64"],
                },
            ),
            Tool(
                name="generate_floorplan_preview_from_base64",
                description="Generate a quick preview PNG of the floorplan without full processing. Faster than full generation.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_base64": {
                            "type": "string",
                            "description": "Base64-encoded image data of a 360-degree panorama (JPEG or PNG)",
                        }
                    },
                    "required": ["image_base64"],
                },
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent]:
        """Execute MCP tool calls"""
        if name == "generate_floorplan_from_base64":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://127.0.0.1:8000/mcp/generate",
                        json={"image_base64": arguments.get("image_base64")},
                    )
                    if response.status_code == 200:
                        result = response.json()
                        return [TextContent(
                            type="text",
                            text=json.dumps(result, indent=2),
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Error: {response.status_code} - {response.text}",
                        )]
            except Exception as e:
                log.exception("Tool call failed")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
                
        elif name == "generate_floorplan_preview_from_base64":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://127.0.0.1:8000/mcp/generate-preview",
                        json={"image_base64": arguments.get("image_base64")},
                    )
                    if response.status_code == 200:
                        # Return as image content
                        image_data = base64.b64encode(response.content).decode()
                        return [types.ImageContent(
                            type="image",
                            data=image_data,
                            mimeType="image/png",
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Error: {response.status_code} - {response.text}",
                        )]
            except Exception as e:
                log.exception("Tool call failed")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    return server