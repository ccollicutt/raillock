"""
Raillock - A Python library for MCP clients to validate and manage tool access.

This library provides functionality to:
- Connect to MCP servers
- Validate available tools
- Manage tool access permissions
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from .client import RailLockClient
from .config import RailLockConfig
from .exceptions import RailLockError

# Make raillock.commands a package for CLI subcommands

__all__ = ["RailLockClient", "RailLockConfig", "RailLockError"]
