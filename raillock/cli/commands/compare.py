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
from raillock.config_utils import (
    compare_config_with_server,
    handle_config_load_error,
    handle_raillock_error,
)
import yaml


def run_compare(args):
    # Load configuration
    try:
        config = RailLockConfig.from_file(args.config)
    except Exception as e:
        handle_config_load_error(e, args.config)
    client = RailLockClient(config)
    try:
        if getattr(args, "sse", False):

            async def compare_sse():
                try:
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

                    # Use shared comparison function
                    config_data = {
                        "allowed_tools": config.allowed_tools,
                        "malicious_tools": config.malicious_tools,
                        "denied_tools": config.denied_tools,
                    }
                    comparison_data, _ = compare_config_with_server(
                        config_data, server_tools
                    )

                    GREEN = "\033[92m"
                    RED = "\033[91m"
                    RESET = "\033[0m"

                    def check(v):
                        return f"{GREEN}✔{RESET}" if v else f"{RED}✘{RESET}"

                    rows = []
                    for item in comparison_data:
                        rows.append(
                            [
                                item["tool"],
                                check(item["on_server"]),
                                check(item["allowed"]),
                                check(item["checksum_match"]),
                                item["type"],
                                item["description"],
                            ]
                        )

                    headers = [
                        "Tool",
                        "On Server",
                        "Allowed",
                        "Checksum Match",
                        "Type",
                        "Description",
                    ]
                    print(tabulate(rows, headers, tablefmt="fancy_grid"))
                except Exception as e:
                    print(f"Error: {str(e)}", file=sys.stderr)
                    sys.exit(1)

            asyncio.run(compare_sse())
        else:
            client.connect(args.server)
            server_tools = client._available_tools

            # Use shared comparison function
            config_data = {
                "allowed_tools": config.allowed_tools,
                "malicious_tools": config.malicious_tools,
                "denied_tools": config.denied_tools,
            }
            comparison_data, _ = compare_config_with_server(config_data, server_tools)

            GREEN = "\033[92m"
            RED = "\033[91m"
            RESET = "\033[0m"

            def check(v):
                return f"{GREEN}✔{RESET}" if v else f"{RED}✘{RESET}"

            rows = []
            for item in comparison_data:
                rows.append(
                    [
                        item["tool"],
                        check(item["on_server"]),
                        check(item["allowed"]),
                        check(item["checksum_match"]),
                        item["type"],
                        item["description"],
                    ]
                )

            headers = [
                "Tool",
                "On Server",
                "Allowed",
                "Checksum Match",
                "Type",
                "Description",
            ]
            print(tabulate(rows, headers, tablefmt="fancy_grid"))
    except Exception as e:
        handle_raillock_error(e)
    finally:
        client.close()
