#!/usr/bin/env -S ./.venv/bin/python
"""
Echo MCP Client Example with RailLock validation
"""

import asyncio
import logging
import traceback
import sys
import os
from pathlib import Path

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

print("Python executable:", sys.executable)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from raillock import RailLockClient, RailLockConfig
from raillock.mcp_utils import RailLockSessionWrapper

# Determine absolute path to server script
SCRIPT_DIR = Path(__file__).parent.resolve()
SERVER_SCRIPT_PATH = SCRIPT_DIR / "echo_server.py"

# Set up logging to both file and console
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("echo_raillock_client.log")
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(console_handler)

# RailLock config: only allow the 'echo' tool
ALLOWED_TOOLS = {
    "echo": "*"
}  # Accept any checksum for demo; in production, use the real checksum
rail_config = RailLockConfig(allowed_tools=ALLOWED_TOOLS)
rail_client = RailLockClient(rail_config)


async def main():
    logger.debug("Starting echo client main() with RailLock")
    server_params = StdioServerParameters(
        command="python", args=[str(SERVER_SCRIPT_PATH)], env=None
    )
    logger.debug(f"Server parameters: {server_params}")

    try:
        logger.debug("Opening stdio_client context")
        async with stdio_client(server_params) as (read_stream, write_stream):
            logger.debug("Opened stdio_client context")
            async with ClientSession(read_stream, write_stream) as session:
                logger.debug("ClientSession context entered, initializing session")
                await session.initialize()
                logger.debug("Session initialized")

                # Use RailLockSessionWrapper to always filter and inject descriptions
                wrapper = RailLockSessionWrapper(session, rail_client)
                filtered_tools = await wrapper.list_tools()
                tool_names = [tool.name for tool in filtered_tools]
                logger.info(f"Available tools (filtered by RailLock): {tool_names}")

                # Only try allowed tools
                for tool in filtered_tools:
                    # Try both echo and add tools
                    for tool_to_try, params in [
                        ("echo", {"text": "Hello, MCP with RailLock!"}),
                        ("add", {"a": 1, "b": 2}),
                    ]:
                        if tool.name == tool_to_try:
                            allowed = tool.name in rail_client.config.allowed_tools
                            msg = f"Tool '{tool.name}' allowed by RailLock: {allowed}"
                            if allowed:
                                logger.info(GREEN + msg + RESET)
                                result = await session.call_tool(tool_to_try, params)
                                logger.info(
                                    YELLOW
                                    + f"{tool_to_try.capitalize()} result: {getattr(result, 'content', result)}"
                                    + RESET
                                )
                            else:
                                logger.warning(
                                    RED
                                    + f"Tool '{tool.name}' is not allowed by RailLock policy!"
                                    + RESET
                                )
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.debug("Exiting echo client main() with RailLock")


if __name__ == "__main__":
    asyncio.run(main())
