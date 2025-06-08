import sys
import traceback
import hashlib
import yaml
import asyncio
import textwrap
from raillock.client import RailLockClient
from raillock.config import RailLockConfig
from raillock.exceptions import RailLockError
from raillock.mcp_utils import get_tools_via_sse
from raillock.utils import calculate_tool_checksum
from raillock.config_utils import (
    build_config_dict,
    save_config_to_file,
    handle_config_load_error,
    handle_raillock_error,
    extract_tool_info,
)

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def interactive_review_tools(tools, server_name, server_type, output_file=None):
    """Interactive tool review using shared utilities."""
    choices = {}

    for tool in tools:
        name, desc = extract_tool_info(tool)

        print(f"\n{name}:")
        print(f"  Description: {desc}")
        ynmi = (
            input(f"Allow tool '{name}'? {GREEN}[y]{RESET}/{RED}m{RESET}/n/i: ")
            .strip()
            .lower()
        )

        if ynmi == "y":
            choices[name] = "allow"
        elif ynmi == "m":
            choices[name] = "malicious"
        elif ynmi == "n":
            choices[name] = "deny"
        # else: ignore (do not record)

    # Build config using shared utility
    config_dict = build_config_dict(tools, choices, server_name, server_type)

    # Save config using shared utility
    if output_file:
        out_path = output_file
    else:
        out_path = (
            input("Enter output YAML config filename [raillock_config.yaml]: ").strip()
            or "raillock_config.yaml"
        )

    save_config_to_file(config_dict, out_path)
    print(f"RailLock config saved to {out_path}")


def run_review(args):
    # If --yes is set, treat --config as output file, not input
    config = None
    output_file = None
    if getattr(args, "yes", False):
        # --yes: config is output file, do not load
        config = RailLockConfig()
        output_file = getattr(args, "config", None)
    else:
        # Not --yes: config is input file
        if getattr(args, "config", None):
            try:
                print(f"[DEBUG] Loading config from {args.config}")
                config = RailLockConfig.from_file(args.config)
            except Exception as e:
                handle_config_load_error(e, args.config)
        else:
            config = RailLockConfig()

    # Create client
    client = RailLockClient(config)

    try:
        print(f"\n=== RailLock Review Mode ===")
        print(f"You are reviewing tools from server: {args.server}")
        if getattr(args, "sse", False):
            print(
                "\nYou will be prompted to allow or deny each tool. Press Ctrl+C to exit at any time.\n"
            )
        else:
            print("\nThis will display all available tools and their info.\n")
        print("---\n")
        print(f"Testing server availability...")
        client.test_server(args.server, timeout=getattr(args, "timeout", 30))
        print(
            f"Server is up. Connecting to server: {args.server} (sse={getattr(args, 'sse', False)})"
        )

        def write_config(config_dict):
            nonlocal output_file
            if output_file:
                out_path = output_file
            else:
                out_path = (
                    input(
                        "Enter output YAML config filename [raillock_config.yaml]: "
                    ).strip()
                    or "raillock_config.yaml"
                )

            save_config_to_file(config_dict, out_path)
            print(f"RailLock config saved to {out_path}")

        if getattr(args, "sse", False):
            # Use MCP protocol for SSE
            async def review_sse():
                try:
                    tools, real_server_name = await get_tools_via_sse(args.server)
                    print("[DEBUG] Raw tools from server:", tools)
                    if getattr(args, "yes", False):
                        config_dict = {
                            "config_version": 1,
                            "server": {
                                "name": real_server_name or args.server,
                                "type": "sse",
                            },
                            "allowed_tools": {},
                            "malicious_tools": {},
                            "denied_tools": {},
                        }
                        for tool in tools:
                            name = getattr(tool, "name", None)
                            desc = getattr(tool, "description", "")
                            checksum = calculate_tool_checksum(
                                name, desc, config_dict["server"]["name"]
                            )
                            config_dict["allowed_tools"][name] = {
                                "description": desc,
                                "server": config_dict["server"]["name"],
                                "checksum": checksum,
                            }
                        write_config(config_dict)
                    else:
                        interactive_review_tools(
                            tools,
                            real_server_name or args.server,
                            "sse",
                            output_file,
                        )
                except Exception as e:
                    print(f"Error: {str(e)}", file=sys.stderr)
                    sys.exit(1)

            try:
                asyncio.run(review_sse())
            except KeyboardInterrupt:
                print("\n[INFO] Review cancelled by user (Ctrl+C). Exiting.")
                sys.exit(130)
        elif getattr(args, "yes", False):
            # STDIO or HTTP mode, auto-accept all tools and write config
            client.connect(args.server)
            tools = client._available_tools
            config_dict = {
                "config_version": 1,
                "server": {
                    "name": args.server,
                    "type": "stdio" if args.server.startswith("stdio:") else "http",
                },
                "allowed_tools": {},
                "malicious_tools": {},
                "denied_tools": {},
            }
            for name, tool in tools.items():
                desc = tool["description"]
                checksum = tool["checksum"]
                config_dict["allowed_tools"][name] = {
                    "description": desc,
                    "server": config_dict["server"]["name"],
                    "checksum": checksum,
                }
            write_config(config_dict)
        else:
            client.connect(args.server)
            print("[DEBUG] Connected. Reviewing tools...")
            # Use the new interactive review for stdio/http
            tools = []
            for name, tool in client._available_tools.items():
                tools.append({"name": name, "description": tool["description"]})
            interactive_review_tools(
                tools,
                args.server,
                "stdio" if args.server.startswith("stdio:") else "http",
                output_file,
            )
    except Exception as e:
        handle_raillock_error(e)
    finally:
        client.close()
