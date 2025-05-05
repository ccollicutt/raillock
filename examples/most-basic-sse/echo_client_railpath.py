#!/usr/bin/env -S ./.venv/bin/python
"""
Echo MCP SSE Client Example with RailLock validation
"""

import asyncio
import logging
import traceback
import sys
import os
from pathlib import Path
from mcp.client.sse import sse_client
from mcp import ClientSession

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from raillock import RailLockClient, RailLockConfig

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

print("Python executable:", sys.executable)

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
    logger.debug("Starting echo SSE client main() with RailLock")
    try:
        async with sse_client("http://127.0.0.1:8000/sse") as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                logger.debug("Session initialized")

                # List available tools
                response = await session.list_tools()
                tool_names = [tool.name for tool in response.tools]
                logger.info(f"Available tools: {tool_names}")

                # RailLock: validate tool access
                for tool in response.tools:
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
        logger.debug("Exiting echo SSE client main() with RailLock")


if __name__ == "__main__":
    asyncio.run(main())
