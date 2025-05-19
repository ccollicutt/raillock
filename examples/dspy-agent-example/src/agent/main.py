import dspy
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from agent import RAILLOCK_CLIENT

# Only import monkeypatch if RailLock is enabled
if RAILLOCK_CLIENT is not None:
    from raillock.mcp_utils import monkeypatch_raillock_tools

# Compute absolute path to mcp-server/server.py
SERVER_SCRIPT_PATH = str(
    Path(__file__).parent.parent.parent / "mcp-server" / "server.py"
)

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",  # Executable
    args=[SERVER_SCRIPT_PATH],
    env=None,
)


# 1. Define the DSPy Signature
class DSPyAirlineCustomerService(dspy.Signature):
    """You are an airline customer service agent. You are given a list of tools to handle user requests.
    You should decide the right tool to use in order to fulfill users' requests."""

    user_request: str = dspy.InputField()
    process_result: str = dspy.OutputField(
        desc=(
            "Message that summarizes the process result, and the information users need, "
            "e.g., the confirmation_number if it's a flight booking request."
        )
    )


# 2. Configure DSPy with a language model
dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))  # You can change the model if needed


# 3. Gather tools and build the agent
async def run(user_request):
    async with stdio_client(server_params) as (read, write):
        print(
            "[DEBUG] Using server command:", server_params.command, server_params.args
        )
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Print all tools and their checksums before RailLock filtering
            tools_pre = await session.list_tools()
            for tool in tools_pre.tools:
                print(f"[DEBUG] Tool: {tool.name}, Description: {tool.description}")
                from raillock.utils import calculate_tool_checksum

                print(
                    "[DEBUG] Checksum:",
                    calculate_tool_checksum(tool.name, tool.description, None),
                )

            # RailLock monkeypatch if enabled
            if RAILLOCK_CLIENT is not None:
                monkeypatch_raillock_tools(session, RAILLOCK_CLIENT)

            tools = await session.list_tools()

            if RAILLOCK_CLIENT is not None:
                print("[DEBUG] RailLock client is enabled")
                print(
                    "[DEBUG] Tools before RailLock filtering:",
                    [tool.name for tool in tools.tools],
                )
            else:
                print("[DEBUG] RailLock client is disabled")

            dspy_tools = [
                dspy.Tool.from_mcp_tool(session, tool) for tool in tools.tools
            ]
            print("[DEBUG] dspy_tools:", [tool.name for tool in dspy_tools])

            react = dspy.ReAct(DSPyAirlineCustomerService, tools=dspy_tools)
            result = await react.acall(user_request=user_request)
            print(result)


if __name__ == "__main__":
    import asyncio

    # Example user request
    asyncio.run(
        run(
            "please help me book a flight from SFO to JFK on 09/01/2025, my name is Adam"
        )
    )
