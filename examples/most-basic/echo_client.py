"""
Echo MCP Client Example
"""

import asyncio
import logging
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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
    logger.debug("Starting echo client main()")
    # Set up the server parameters (launches the server as a subprocess)
    server_params = StdioServerParameters(
        command="python", args=["echo_server.py"], env=None
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
        logger.debug("Exiting echo client main()")


if __name__ == "__main__":
    asyncio.run(main())
