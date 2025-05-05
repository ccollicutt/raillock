#! /usr/bin/env python3

"""
Echo MCP Server Example
"""

import sys
import os

print("[DEBUG] echo_server.py sys.executable:", sys.executable)
print("[DEBUG] echo_server.py sys.path:", sys.path)
print("[DEBUG] echo_server.py VIRTUAL_ENV:", os.environ.get("VIRTUAL_ENV"))
try:
    import mcp

    print("[DEBUG] mcp module found:", mcp)
except ImportError as e:
    print("[DEBUG] mcp import error:", e)

# Set log level to WARNING or higher, and log to file
os.environ["FASTMCP_LOG_LEVEL"] = "DEBUG"
import logging

logging.basicConfig(filename="echo_server.log", level=logging.DEBUG)

from mcp.server.fastmcp import FastMCP

# Create the server
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
def subtract(a: int, b: int) -> int:
    """Subtract two integers"""
    return a - b


if __name__ == "__main__":
    mcp.run(transport="stdio")
