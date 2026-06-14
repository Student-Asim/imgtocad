#!/usr/bin/env python3
"""
MCP Server for MagicPlan Floorplan Generation
Exposes floorplan generation capabilities to Claude and other MCP clients
"""

import asyncio
import base64
import json
import logging
import sys
from io import BytesIO

import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent
import mcp.types as types
import mcp.server.stdio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("magicplan_mcp")

# API endpoint configuration
API_BASE_URL = "http://127.0.0.1:8000"

# Create MCP server
server = Server("magicplan-floorplan")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools for floorplan generation"""
    log.debug("Listing tools")
    return [
        Tool(
            name="generate_floorplan_from_image",
            description="Generate a 2D CAD floorplan from a 360-degree panorama image. Returns a PNG preview, DXF file for CAD, and debug visualizations showing detected walls, openings, and furniture.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64-encoded image data of a 360-degree panorama. Supported formats: JPEG, PNG. Typical size: 4096x2048 or higher.",
                    },
                    "include_debug": {
                        "type": "boolean",
                        "description": "Include debug visualization layers (layout detection, openings, furniture). Default: true",
                        "default": True,
                    },
                },
                "required": ["image_base64"],
            },
        ),
        Tool(
            name="generate_floorplan_preview",
            description="Generate a quick preview PNG of the floorplan without full processing. Much faster than full generation, returns only the preview image.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64-encoded image data of a 360-degree panorama. Supported formats: JPEG, PNG.",
                    },
                },
                "required": ["image_base64"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent]:
    """Execute MCP tool calls by proxying to the FastAPI backend"""
    log.debug(f"Tool called: {name} with arguments: {arguments.keys()}")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            if name == "generate_floorplan_from_image":
                log.info("Generating full floorplan...")
                
                # Call the backend API
                response = await client.post(
                    f"{API_BASE_URL}/mcp/generate",
                    json={"image_base64": arguments.get("image_base64")},
                )
                log.debug(f"Backend response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Format detailed response
                    response_text = f"""✅ Floorplan generation successful!

📊 Room Analysis:
- Room Size: {result.get('room_size_m', 'N/A')} m²
- Walls: {len(result.get('walls', []))} detected
- Openings (doors/windows): {len(result.get('openings', []))} detected
- Furniture items: {len(result.get('furniture', []))} detected

📥 Generated Files:
- PNG Preview: {result.get('download_png', 'N/A')}
- DXF CAD File: {result.get('download_dxf', 'N/A')}
- Job ID: {result.get('job_id', 'N/A')}

🔍 Debug Information:
- Layout Detection Debug: {result.get('debug_layout_png', 'N/A')}
- Openings Detection Debug: {result.get('debug_openings_png', 'N/A')}
- Furniture Detection Debug: {result.get('debug_furniture_png', 'N/A')}

📋 Full Result:
{json.dumps(result, indent=2)}
"""
                    return [TextContent(type="text", text=response_text)]
                else:
                    error_text = f"API Error {response.status_code}: {response.text}"
                    log.error(error_text)
                    return [TextContent(type="text", text=error_text)]
                    
            elif name == "generate_floorplan_preview":
                log.info("Generating floorplan preview...")
                
                response = await client.post(
                    f"{API_BASE_URL}/mcp/generate-preview",
                    json={"image_base64": arguments.get("image_base64")},
                )
                log.debug(f"Backend response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Return as base64 image
                    image_base64 = base64.b64encode(response.content).decode()
                    return [ImageContent(
                        type="image",
                        data=image_base64,
                        mimeType="image/png",
                    )]
                else:
                    error_text = f"API Error {response.status_code}: {response.text}"
                    log.error(error_text)
                    return [TextContent(type="text", text=error_text)]
                    
            else:
                error_text = f"Unknown tool: {name}"
                log.error(error_text)
                return [TextContent(type="text", text=error_text)]
                
    except httpx.ConnectError as e:
        error_text = f"Cannot connect to API at {API_BASE_URL}. Is the FastAPI server running? Error: {e}"
        log.error(error_text)
        return [TextContent(type="text", text=error_text)]
    except asyncio.TimeoutError:
        error_text = "Floorplan generation timed out (>5 minutes). Try with a smaller image or simpler scene."
        log.error(error_text)
        return [TextContent(type="text", text=error_text)]
    except Exception as e:
        error_text = f"Unexpected error: {type(e).__name__}: {str(e)}"
        log.exception(error_text)
        return [TextContent(type="text", text=error_text)]


async def main():
    """Main entry point for the MCP server"""
    log.info("Starting MagicPlan Floorplan MCP Server")
    log.info(f"API Backend: {API_BASE_URL}")
    # Use the stdio transport so the process can be launched by Claude Desktop
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        init_opts = server.create_initialization_options()
        log.info("MCP Server running and ready for connections over stdio")
        await server.run(read_stream, write_stream, init_opts)


if __name__ == "__main__":
    asyncio.run(main())
