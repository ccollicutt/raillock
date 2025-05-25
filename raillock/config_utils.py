"""Shared utilities for configuration building and YAML handling."""

import textwrap
import yaml
import sys
import traceback
from typing import Dict, Any, List


def build_config_dict(
    tools: List[Dict], choices: Dict[str, str], server_name: str, server_type: str
) -> Dict[str, Any]:
    """Build a configuration dictionary from tools and user choices.

    Args:
        tools: List of tool dictionaries with 'name' and 'description'
        choices: Dictionary mapping tool names to choice ('allow', 'deny', 'malicious')
        server_name: Name of the server
        server_type: Type of server ('sse', 'stdio', 'http')

    Returns:
        Configuration dictionary ready for YAML serialization
    """
    from raillock.utils import calculate_tool_checksum

    config_dict = {
        "config_version": 1,
        "server": {
            "name": server_name,
            "type": server_type,
        },
        "allowed_tools": {},
        "malicious_tools": {},
        "denied_tools": {},
    }

    for tool in tools:
        # Handle both dict and object formats
        name, desc = extract_tool_info(tool)

        choice = choices.get(name)
        if choice:
            checksum = calculate_tool_checksum(name, desc, server_name)
            tool_entry = {
                "description": desc,
                "server": server_name,
                "checksum": checksum,
            }

            if choice == "allow":
                config_dict["allowed_tools"][name] = tool_entry
            elif choice == "malicious":
                config_dict["malicious_tools"][name] = tool_entry
            elif choice == "deny":
                config_dict["denied_tools"][name] = tool_entry

    # Dedent all descriptions before writing
    for section in ("allowed_tools", "malicious_tools", "denied_tools"):
        for tool in config_dict.get(section, {}).values():
            if "description" in tool and isinstance(tool["description"], str):
                tool["description"] = textwrap.dedent(tool["description"]).strip("\n")

    return config_dict


def get_yaml_str_presenter():
    """Get a YAML string presenter function for consistent formatting."""

    def str_presenter(dumper, data):
        # Always use block style for multi-line strings
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        if any(c in data for c in [":", '"', "'", "{", "}", "[", "]"]):
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    return str_presenter


def save_config_to_file(config_dict: Dict[str, Any], filename: str) -> None:
    """Save configuration dictionary to YAML file with consistent formatting.

    Args:
        config_dict: Configuration dictionary
        filename: Path to output file
    """
    # Ensure filename has .yaml extension
    if not filename.endswith((".yaml", ".yml")):
        filename += ".yaml"

    yaml.add_representer(str, get_yaml_str_presenter())

    with open(filename, "w") as f:
        yaml.safe_dump(config_dict, f, sort_keys=False, allow_unicode=True)


def config_dict_to_yaml_string(config_dict: Dict[str, Any]) -> str:
    """Convert configuration dictionary to YAML string.

    Args:
        config_dict: Configuration dictionary

    Returns:
        YAML string representation
    """
    yaml.add_representer(str, get_yaml_str_presenter())
    return yaml.safe_dump(config_dict, sort_keys=False, allow_unicode=True)


def compare_config_with_server(config_data: dict, server_tools: dict) -> tuple:
    """Compare a configuration with server tools and return comparison data and summary.

    Args:
        config_data: Parsed configuration dictionary
        server_tools: Dictionary of server tools with checksums

    Returns:
        Tuple of (comparison_data, summary)
    """
    # Extract config sections
    allowed_tools = config_data.get("allowed_tools", {})
    malicious_tools = config_data.get("malicious_tools", {})
    denied_tools = config_data.get("denied_tools", {})

    # Get all unique tool names
    all_tool_names = (
        set(server_tools.keys())
        | set(allowed_tools.keys())
        | set(malicious_tools.keys())
        | set(denied_tools.keys())
    )

    # Perform comparison
    comparison_data = []

    for tool in sorted(all_tool_names):
        on_server = tool in server_tools
        allowed = tool in allowed_tools

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
            allowed_checksum = None
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

        # Determine tool type
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

        # Get description
        desc = ""
        if on_server:
            desc = server_tools[tool]["description"]
        elif allowed and isinstance(allowed_tools[tool], dict):
            desc = allowed_tools[tool].get("description", "")

        comparison_data.append(
            {
                "tool": tool,
                "on_server": on_server,
                "allowed": allowed,
                "checksum_match": checksum_match,
                "type": tool_type,
                "description": desc,
            }
        )

    # Generate summary
    summary = {
        "server_tools": len(server_tools),
        "allowed_tools": len(allowed_tools),
        "malicious_tools": len(malicious_tools),
        "denied_tools": len(denied_tools),
        "checksum_mismatches": len(
            [
                item
                for item in comparison_data
                if not item["checksum_match"] and item["on_server"]
            ]
        ),
    }

    return comparison_data, summary


def handle_config_load_error(e: Exception, config_path: str):
    """Handle common configuration loading errors consistently."""
    if isinstance(e, (ValueError, yaml.YAMLError)):
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


def handle_raillock_error(e: Exception):
    """Handle common RailLock errors consistently."""
    from raillock.exceptions import RailLockError

    if isinstance(e, KeyboardInterrupt):
        print("\n[INFO] Operation cancelled by user (Ctrl+C). Exiting.")
        sys.exit(130)
    elif isinstance(e, RailLockError):
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def extract_tool_info(tool):
    """Extract name and description from tool object or dict consistently.

    Args:
        tool: Tool object or dictionary

    Returns:
        Tuple of (name, description)
    """
    if isinstance(tool, dict):
        name = tool.get("name")
        desc = tool.get("description", "")
    else:
        name = getattr(tool, "name", None)
        desc = getattr(tool, "description", "")
    return name, desc
