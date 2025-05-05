"""
RailLockConfig - Configuration management for tool validation.
"""

import yaml
from pathlib import Path
from typing import Dict, Optional


class RailLockConfig:
    """Configuration class for managing allowed tools and their checksums."""

    def __init__(self, allowed_tools: Optional[Dict[str, str]] = None):
        """Initialize the configuration with allowed tools and their checksums."""
        self.allowed_tools = allowed_tools or {}

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

        if not isinstance(config_data, dict):
            raise ValueError("Configuration file must contain a YAML mapping/object")

        # If 'allowed_tools' is present, use it; otherwise, use the whole dict
        allowed_tools = config_data.get("allowed_tools", config_data)
        return cls(allowed_tools)
