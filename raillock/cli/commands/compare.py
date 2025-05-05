import sys
import traceback
import hashlib
import asyncio
from tabulate import tabulate
from raillock.client import RailLockClient
from raillock.config import RailLockConfig
from raillock.exceptions import RailLockError
from raillock.mcp_utils import get_tools_via_sse
from raillock.utils import calculate_tool_checksum


def run_compare(args):
    # Load configuration
    try:
        config = RailLockConfig.from_file(args.config)
    except Exception as e:
        print(f"Error loading configuration: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    client = RailLockClient(config)
    try:
        if getattr(args, "sse", False):

            async def compare_sse():
                tools, _ = await get_tools_via_sse(args.server)
                server_tools = {
                    t.name: {
                        "description": t.description,
                        "checksum": calculate_tool_checksum(
                            t.name, t.description, args.server
                        ),
                    }
                    for t in tools
                }
                allowed_tools = config.allowed_tools
                all_tool_names = set(server_tools.keys()) | set(allowed_tools.keys())
                GREEN = "\033[92m"
                RED = "\033[91m"
                RESET = "\033[0m"

                def check(v):
                    return f"{GREEN}✔{RESET}" if v else f"{RED}✘{RESET}"

                rows = []
                for tool in sorted(all_tool_names):
                    on_server = tool in server_tools
                    allowed = tool in allowed_tools
                    allowed_checksum = None
                    if allowed:
                        allowed_val = allowed_tools[tool]
                        if isinstance(allowed_val, dict) and "checksum" in allowed_val:
                            allowed_checksum = allowed_val["checksum"]
                        elif isinstance(allowed_val, str):
                            allowed_checksum = allowed_val
                    server_checksum = (
                        server_tools[tool]["checksum"] if on_server else None
                    )
                    checksum_match = (
                        on_server
                        and allowed
                        and allowed_checksum is not None
                        and server_checksum == allowed_checksum
                    )
                    desc = (
                        server_tools[tool]["description"]
                        if on_server
                        else (
                            allowed_tools[tool].get("description", "")
                            if allowed and isinstance(allowed_tools[tool], dict)
                            else ""
                        )
                    )
                    rows.append(
                        [
                            tool,
                            check(on_server),
                            check(allowed),
                            check(checksum_match),
                            desc,
                        ]
                    )
                headers = [
                    "Tool",
                    "On Server",
                    "Allowed",
                    "Checksum Match",
                    "Description",
                ]
                print(tabulate(rows, headers, tablefmt="fancy_grid"))

            asyncio.run(compare_sse())
        else:
            client.connect(args.server)
            server_tools = client._available_tools
            allowed_tools = config.allowed_tools
            all_tool_names = set(server_tools.keys()) | set(allowed_tools.keys())
            GREEN = "\033[92m"
            RED = "\033[91m"
            RESET = "\033[0m"

            def check(v):
                return f"{GREEN}✔{RESET}" if v else f"{RED}✘{RESET}"

            rows = []
            for tool in sorted(all_tool_names):
                on_server = tool in server_tools
                allowed = tool in allowed_tools
                allowed_checksum = None
                if allowed:
                    allowed_val = allowed_tools[tool]
                    if isinstance(allowed_val, dict) and "checksum" in allowed_val:
                        allowed_checksum = allowed_val["checksum"]
                    elif isinstance(allowed_val, str):
                        allowed_checksum = allowed_val
                server_checksum = server_tools[tool]["checksum"] if on_server else None
                checksum_match = (
                    on_server
                    and allowed
                    and allowed_checksum is not None
                    and server_checksum == allowed_checksum
                )
                desc = (
                    server_tools[tool]["description"]
                    if on_server
                    else (
                        allowed_tools[tool].get("description", "")
                        if allowed and isinstance(allowed_tools[tool], dict)
                        else ""
                    )
                )
                rows.append(
                    [
                        tool,
                        check(on_server),
                        check(allowed),
                        check(checksum_match),
                        desc,
                    ]
                )
            headers = [
                "Tool",
                "On Server",
                "Allowed",
                "Checksum Match",
                "Description",
            ]
            print(tabulate(rows, headers, tablefmt="fancy_grid"))
    except Exception as e:
        print(f"Error comparing tools: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()
