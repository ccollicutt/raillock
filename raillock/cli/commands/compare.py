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
import yaml


def run_compare(args):
    # Load configuration
    try:
        config = RailLockConfig.from_file(args.config)
    except (ValueError, yaml.YAMLError) as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
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
                    allowed_tools = config.allowed_tools
                    malicious_tools = config.malicious_tools
                    denied_tools = config.denied_tools
                    all_tool_names = set(server_tools.keys()) | set(
                        allowed_tools.keys()
                    )
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
                        # Check for malicious and denied by name+checksum
                        is_malicious = False
                        is_denied = False
                        name_in_section = False
                        checksum_match = False
                        if tool in malicious_tools and on_server:
                            name_in_section = True
                            mal_entry = malicious_tools[tool]
                            if isinstance(mal_entry, dict) and "checksum" in mal_entry:
                                if (
                                    server_tools[tool]["checksum"]
                                    == mal_entry["checksum"]
                                ):
                                    is_malicious = True
                                    checksum_match = True
                                else:
                                    checksum_match = False
                        if tool in denied_tools and on_server:
                            name_in_section = True
                            den_entry = denied_tools[tool]
                            if isinstance(den_entry, dict) and "checksum" in den_entry:
                                if (
                                    server_tools[tool]["checksum"]
                                    == den_entry["checksum"]
                                ):
                                    is_denied = True
                                    checksum_match = True
                                else:
                                    checksum_match = False
                        if allowed:
                            allowed_val = allowed_tools[tool]
                            if isinstance(allowed_val, dict):
                                if "checksum" in allowed_val:
                                    allowed_checksum = allowed_val["checksum"]
                            elif isinstance(allowed_val, str):
                                allowed_checksum = allowed_val
                            if on_server and allowed_checksum is not None:
                                if server_tools[tool]["checksum"] == allowed_checksum:
                                    checksum_match = True
                                else:
                                    checksum_match = False
                                name_in_section = True
                        tool_type = (
                            "allowed"
                            if allowed and checksum_match
                            else (
                                "malicious"
                                if is_malicious
                                else (
                                    "denied"
                                    if is_denied
                                    else (
                                        "unknown (checksum mismatch)"
                                        if name_in_section and not checksum_match
                                        else "unknown"
                                    )
                                )
                            )
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
                                tool_type,
                                desc,
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
            allowed_tools = config.allowed_tools
            malicious_tools = config.malicious_tools
            denied_tools = config.denied_tools
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
                # Check for malicious and denied by name+checksum
                is_malicious = False
                is_denied = False
                name_in_section = False
                checksum_match = False
                if tool in malicious_tools and on_server:
                    name_in_section = True
                    mal_entry = malicious_tools[tool]
                    if isinstance(mal_entry, dict) and "checksum" in mal_entry:
                        if server_tools[tool]["checksum"] == mal_entry["checksum"]:
                            is_malicious = True
                            checksum_match = True
                        else:
                            checksum_match = False
                if tool in denied_tools and on_server:
                    name_in_section = True
                    den_entry = denied_tools[tool]
                    if isinstance(den_entry, dict) and "checksum" in den_entry:
                        if server_tools[tool]["checksum"] == den_entry["checksum"]:
                            is_denied = True
                            checksum_match = True
                        else:
                            checksum_match = False
                if allowed:
                    allowed_val = allowed_tools[tool]
                    if isinstance(allowed_val, dict):
                        if "checksum" in allowed_val:
                            allowed_checksum = allowed_val["checksum"]
                    elif isinstance(allowed_val, str):
                        allowed_checksum = allowed_val
                    if on_server and allowed_checksum is not None:
                        if server_tools[tool]["checksum"] == allowed_checksum:
                            checksum_match = True
                        else:
                            checksum_match = False
                        name_in_section = True
                tool_type = (
                    "allowed"
                    if allowed and checksum_match
                    else (
                        "malicious"
                        if is_malicious
                        else (
                            "denied"
                            if is_denied
                            else (
                                "unknown (checksum mismatch)"
                                if name_in_section and not checksum_match
                                else "unknown"
                            )
                        )
                    )
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
                        tool_type,
                        desc,
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
    except RailLockError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()
