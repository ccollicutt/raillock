"""
Raillock - A Python library for MCP clients to validate and manage tool access.

This library provides functionality to:
- Connect to MCP servers
- Validate available tools
- Manage tool access permissions
"""

__version__ = "0.1.0"
__author__ = "Curtis Collicutt"
__license__ = "MIT"

from .client import RailLockClient
from .config import RailLockConfig
from .exceptions import RailLockError
from .utils import debug_print

# Make raillock.commands a package for CLI subcommands

__all__ = ["RailLockClient", "RailLockConfig", "RailLockError"]

import os


def is_debug():
    return os.environ.get("RAILLOCK_DEBUG", "false").lower() == "true"


# Print import path if debug is enabled
if is_debug():
    import sys

    debug_print("RailLock __init__ loaded from:", __file__)
    debug_print("sys.path:", sys.path)
