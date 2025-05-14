"""
RailLockConfig - Configuration management for tool validation.
"""

import yaml
from pathlib import Path
from typing import Dict, Optional


class RailLockConfig:
    """Configuration class for managing allowed, malicious, and denied tools and their checksums."""

    def __init__(self, allowed_tools=None, malicious_tools=None, denied_tools=None):
        """Initialize the configuration with allowed, malicious, and denied tools and their checksums."""
        self.allowed_tools = allowed_tools or {}
        self.malicious_tools = malicious_tools or {}
        self.denied_tools = denied_tools or {}

    @classmethod
    def from_file(cls, config_path: str) -> "RailLockConfig":
        """Load configuration from a YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(path, "r") as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError:
            raise ValueError(f"Invalid YAML in configuration file: {config_path}")

        validate_config_dict(config_data)

        allowed_tools = config_data.get("allowed_tools", {})
        malicious_tools = config_data.get("malicious_tools", {})
        denied_tools = config_data.get("denied_tools", {})
        return cls(allowed_tools, malicious_tools, denied_tools)


def validate_config_dict(config_data):
    if not isinstance(config_data, dict):
        raise ValueError("Configuration file must contain a YAML mapping/object")
    for section in ("allowed_tools", "malicious_tools", "denied_tools"):
        if section not in config_data:
            raise ValueError(
                f"Missing required section: '{section}' in configuration file"
            )
        if not isinstance(config_data[section], dict):
            raise ValueError(
                f"Section '{section}' must be a mapping/object in configuration file"
            )
    # Optionally, check tool entries
    for section in ("allowed_tools", "malicious_tools", "denied_tools"):
        for tool_name, tool_entry in config_data[section].items():
            if not isinstance(tool_entry, dict):
                raise ValueError(
                    f"Tool '{tool_name}' in section '{section}' must be a mapping/object"
                )
            if section != "denied_tools":
                if "description" not in tool_entry or "checksum" not in tool_entry:
                    raise ValueError(
                        f"Tool '{tool_name}' in section '{section}' must have 'description' and 'checksum'"
                    )
