#!/usr/bin/env -S ./.venv/bin/python
"""
RailLock Demo: Echo MCP Client with RailLock Monkeypatching

This demo shows how RailLock enforces strict tool validation for an MCP client.

- The client connects to an example MCP server (echo_server.py) using stdio.
- It first lists all tools available from the server (unfiltered).
- Then, it applies RailLock filtering (using a config file) to only allow tools that:
    * Are explicitly listed in allowed_tools
    * Have a matching checksum (name, description, and server for SSE/HTTP)
    * Are NOT in denied_tools or malicious_tools (these always take precedence)
- The demo prints:
    * The initial (unfiltered) tool list
    * The filtered tool list (after RailLock)
    * For each tool removed, the reason (malicious, denied, checksum mismatch, or not allowed)
    * The actual and config checksums for a demo tool (check_config)
    * Attempts to call both 'echo' and 'add', showing which are allowed and which are filtered out

This demonstrates RailLock's security guarantees:
- Only tools that match the config and checksum are allowed
- Malicious and denied tools are always blocked
- Tools with a checksum mismatch (e.g., changed description or server) are blocked
- The filtering is auditable and reasons are shown for every removal

To run this demo:
    make echo-client-raillock-monkeypatch

Check the output for clear evidence of RailLock's filtering and security logic in action.
"""

import asyncio
import logging
import traceback
import sys
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from raillock import RailLockClient, RailLockConfig
from raillock.mcp_utils import monkeypatch_raillock_tools
import random

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

print("Python executable:", sys.executable)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Determine absolute path to server script
SCRIPT_DIR = Path(__file__).parent.resolve()
SERVER_SCRIPT_PATH = SCRIPT_DIR / "echo_server.py"

####
# SETUP: Logging, config, and RailLock client
####
# Set up logging to both file and console
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("echo_raillock_client.log")
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(console_handler)

# RailLock config: load from YAML file in the same directory as this script
CONFIG_PATH = SCRIPT_DIR / "raillock_config.yaml"
rail_config = RailLockConfig.from_file(str(CONFIG_PATH))
rail_client = RailLockClient(rail_config)


async def main():
    logger.debug("Starting echo client main() with RailLock monkeypatch")
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

                ####
                # STEP 1: Show initial (unfiltered) tool list from the server
                ####
                unfiltered_response = await session.list_tools()
                unfiltered_tool_names = [
                    tool.name for tool in unfiltered_response.tools
                ]
                logger.info(
                    YELLOW
                    + f"Initial (unfiltered) tools from server: {unfiltered_tool_names}"
                    + RESET
                )

                ####
                # STEP 2: Apply RailLock filtering (monkeypatch) and show filtered tool list
                ####
                monkeypatch_raillock_tools(session, rail_client)
                response = await session.list_tools()
                tool_names = [tool.name for tool in response.tools]
                logger.info(
                    GREEN + f"Filtered tools (by RailLock): {tool_names}" + RESET
                )

                ####
                # STEP 3: For each tool removed, print the reason (malicious, denied, checksum mismatch, or not allowed)
                ####
                filtered_set = set(tool_names)
                unfiltered_set = set(unfiltered_tool_names)
                removed_tools = unfiltered_set - filtered_set
                for tool in removed_tools:
                    reason = None
                    if tool in rail_client.config.malicious_tools:
                        reason = "filtered out as malicious"
                    elif tool in rail_client.config.denied_tools:
                        reason = "filtered out as denied"
                    elif tool in rail_client.config.allowed_tools:
                        # Checksum mismatch
                        unfiltered_tool = next(
                            (t for t in unfiltered_response.tools if t.name == tool),
                            None,
                        )
                        if unfiltered_tool:
                            allowed_entry = rail_client.config.allowed_tools[tool]
                            expected_checksum = allowed_entry["checksum"]
                            from raillock.utils import calculate_tool_checksum

                            actual_checksum = calculate_tool_checksum(
                                tool,
                                unfiltered_tool.description,
                                allowed_entry.get("server"),
                            )
                            if actual_checksum != expected_checksum:
                                reason = "filtered out due to checksum mismatch"
                            else:
                                reason = "filtered out (unknown reason)"
                        else:
                            reason = "filtered out (unknown reason)"
                    else:
                        reason = "filtered out (not in allowed_tools)"
                    logger.warning(
                        RED + f"Tool '{tool}' was removed by RailLock: {reason}" + RESET
                    )

                ####
                # STEP 4: Print actual and config checksums for 'check_config' to demo checksum enforcement
                ####
                for tool in unfiltered_response.tools:
                    if tool.name == "check_config":
                        from raillock.utils import calculate_tool_checksum

                        actual_checksum = calculate_tool_checksum(
                            tool.name,
                            tool.description,
                            rail_client.config.allowed_tools[tool.name].get("server"),
                        )
                        logger.info(
                            YELLOW
                            + f"Server 'check_config' description: {tool.description}"
                            + RESET
                        )
                        logger.info(
                            YELLOW
                            + f"Server 'check_config' checksum: {actual_checksum}"
                            + RESET
                        )
                        logger.info(
                            YELLOW
                            + f"Config 'check_config' checksum: {rail_client.config.allowed_tools[tool.name]['checksum']}"
                            + RESET
                        )

                ####
                # STEP 5: Attempt to call both 'echo' and 'add', showing which are allowed and which are filtered out
                ####
                for tool_to_try, params in [
                    ("echo", {"text": "Hello, MCP with RailLock!"}),
                    ("add", {"a": random.randint(1, 100), "b": random.randint(1, 100)}),
                ]:
                    logger.info(YELLOW + f"Trying to use '{tool_to_try}'..." + RESET)
                    if tool_to_try in tool_names:
                        logger.info(
                            GREEN
                            + f"Tool '{tool_to_try}' is allowed by RailLock."
                            + RESET
                        )
                        result = await session.call_tool(tool_to_try, params)
                        logger.info(
                            YELLOW
                            + f"{tool_to_try.capitalize()} result: {getattr(result, 'content', result)}"
                            + RESET
                        )
                    else:
                        logger.warning(
                            RED
                            + f"Tool '{tool_to_try}' is NOT available (filtered out by RailLock policy)!"
                            + RESET
                        )
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.debug("Exiting echo client main() with RailLock monkeypatch")


if __name__ == "__main__":
    asyncio.run(main())
