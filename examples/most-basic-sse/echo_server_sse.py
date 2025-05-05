"""
Echo MCP Server Example (SSE/HTTP, low-level Server, Starlette)
"""

from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount
import uvicorn
import os

# Define your FastMCP server and tools
mcp = FastMCP("Echo Server")


@mcp.tool()
def echo(text: str) -> str:
    """Echo the input text"""
    return text


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers"""
    return a + b


@mcp.tool()
def delete_folder(folder_path: str) -> str:
    """Delete a folder"""
    import shutil

    # NOTE(curtis): not actually deleting the folder
    return f"Folder {folder_path} deleted successfully"


sse = SseServerTransport("/messages/")


async def handle_sse(request: Request) -> None:
    _server = mcp._mcp_server
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (reader, writer):
        await _server.run(reader, writer, _server.create_initialization_options())


app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="localhost", port=port)
