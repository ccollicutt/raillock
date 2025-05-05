"""
Echo MCP Client Example (SSE/HTTP, low-level)
"""

import asyncio
import logging
import traceback
from mcp.client.sse import sse_client
from mcp import ClientSession

# Set up logging to both file and console
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("echo_client.log")
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(console_handler)


async def main():
    logger.debug("Starting echo client main() (SSE/HTTP)")
    try:
        async with sse_client("http://127.0.0.1:8000/sse") as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                logger.debug("Session initialized")

                # List available tools
                response = await session.list_tools()
                logger.info(
                    f"Available tools: {[tool.name for tool in response.tools]}"
                )

                # Call the echo tool
                result = await session.call_tool("echo", {"text": "Hello, MCP!"})
                logger.info(f"Echo result: {result.content[0].text}")
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.debug("Exiting echo client main() (SSE/HTTP)")


if __name__ == "__main__":
    asyncio.run(main())
