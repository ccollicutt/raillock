import sys
import traceback
import hashlib
import yaml
import asyncio
from raillock.client import RailLockClient
from raillock.config import RailLockConfig
from raillock.exceptions import RailLockError
from raillock.mcp_utils import get_tools_via_sse
from raillock.utils import calculate_tool_checksum


def run_review(args):
    # Load configuration if provided
    config = None
    if getattr(args, "config", None):
        try:
            print(f"[DEBUG] Loading config from {args.config}")
            config = RailLockConfig.from_file(args.config)
        except Exception as e:
            print(f"Error loading configuration: {str(e)}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
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
            output_file = (
                input(
                    "Enter output YAML config filename [raillock_config.yaml]: "
                ).strip()
                or "raillock_config.yaml"
            )

            def str_presenter(dumper, data):
                if "\n" in data:
                    return dumper.represent_scalar(
                        "tag:yaml.org,2002:str", data, style="|"
                    )
                if any(c in data for c in [":", '"', "'", "{", "}", "[", "]"]):
                    return dumper.represent_scalar(
                        "tag:yaml.org,2002:str", data, style='"'
                    )
                return dumper.represent_scalar("tag:yaml.org,2002:str", data)

            yaml.add_representer(str, str_presenter)
            with open(output_file, "w") as f:
                yaml.safe_dump(config_dict, f, sort_keys=False, allow_unicode=True)
            print(f"RailLock config saved to {output_file}")

        if getattr(args, "sse", False):
            # Use MCP protocol for SSE
            async def review_sse():
                tools, real_server_name = await get_tools_via_sse(args.server)
                print("[DEBUG] Raw tools from server:", tools)
                config_dict = {
                    "config_version": 1,
                    "server": {
                        "name": real_server_name or args.server,
                        "type": "sse",
                    },
                    "allowed_tools": {},
                }
                if getattr(args, "yes", False):
                    for tool in tools:
                        name = getattr(tool, "name", None)
                        desc = getattr(tool, "description", "")
                        data = f"{config_dict['server']['name']}:{name}:{desc}".encode(
                            "utf-8"
                        )
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
                    for tool in tools:
                        name = getattr(tool, "name", None)
                        desc = getattr(tool, "description", "")
                        print(f"\n{name}:")
                        print(f"  Description: {desc}")
                        yn = input(f"Allow tool '{name}'? [y/n]: ").strip().lower()
                        if yn == "y":
                            data = (
                                f"{config_dict['server']['name']}:{name}:{desc}".encode(
                                    "utf-8"
                                )
                            )
                            checksum = calculate_tool_checksum(
                                name, desc, config_dict["server"]["name"]
                            )
                            config_dict["allowed_tools"][name] = {
                                "description": desc,
                                "server": config_dict["server"]["name"],
                                "checksum": checksum,
                            }
                    if config_dict["allowed_tools"]:
                        write_config(config_dict)
                    else:
                        print("No tools allowed; config not written.")

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
            from raillock.cli.review_tools import review_tools

            review_tools(client)
    except KeyboardInterrupt:
        print("\n[INFO] Review cancelled by user (Ctrl+C). Exiting.")
        sys.exit(130)
    except RailLockError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"[DEBUG] Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()
