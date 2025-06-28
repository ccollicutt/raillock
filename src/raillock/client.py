"""
RailLockClient - Core client class for MCP server communication and tool validation.
"""

import hashlib
import json
import subprocess
from typing import Dict, Optional
from urllib.parse import urlparse
import asyncio
import os

import requests
from requests.exceptions import RequestException

from .config import RailLockConfig
from .exceptions import RailLockError
from .utils import calculate_tool_checksum
from raillock.utils import debug_print


class RailLockClient:
    """Client for connecting to MCP servers and validating tool access."""

    def __init__(self, config: RailLockConfig):
        """Initialize the client with a configuration."""
        self.config = config
        self._available_tools: Dict[str, dict] = {}
        self._process: Optional[subprocess.Popen] = None
        self._server_name: Optional[str] = None

    def connect(self, server_url: str) -> None:
        """Connect to an MCP server and fetch available tools."""
        self._server_name = server_url
        try:
            if server_url.startswith("stdio:"):
                # Use async stdio_client and ClientSession from MCP SDK
                asyncio.run(self.connect_stdio_async(server_url))
            else:
                # Handle HTTP/SSE transport
                parsed_url = urlparse(server_url)
                if parsed_url.scheme not in ["http", "https"]:
                    raise RailLockError(
                        f"Invalid server URL scheme: {parsed_url.scheme}. "
                        "Use stdio: for subprocess, or http(s):// for network servers."
                    )
                response = requests.get(server_url, timeout=10)
                response.raise_for_status()
                tools_data = response.json()
                self._available_tools = self._parse_tools(tools_data)

        except RequestException as e:
            raise RailLockError(f"Failed to connect to server: {str(e)}")
        except json.JSONDecodeError:
            raise RailLockError("Invalid response format from server")
        except subprocess.SubprocessError as e:
            raise RailLockError(f"Failed to start stdio process: {str(e)}")

    async def connect_async(self, server_url: str) -> None:
        """Async version of connect for use in async contexts."""
        self._server_name = server_url
        try:
            if server_url.startswith("stdio:"):
                await self.connect_stdio_async(server_url)
            else:
                # For HTTP/SSE, we still use synchronous requests
                # Could be improved to use aiohttp in the future
                parsed_url = urlparse(server_url)
                if parsed_url.scheme not in ["http", "https"]:
                    raise RailLockError(
                        f"Invalid server URL scheme: {parsed_url.scheme}. "
                        "Use stdio: for subprocess, or http(s):// for network servers."
                    )
                response = requests.get(server_url, timeout=10)
                response.raise_for_status()
                tools_data = response.json()
                self._available_tools = self._parse_tools(tools_data)

        except RequestException as e:
            raise RailLockError(f"Failed to connect to server: {str(e)}")
        except json.JSONDecodeError:
            raise RailLockError("Invalid response format from server")
        except subprocess.SubprocessError as e:
            raise RailLockError(f"Failed to start stdio process: {str(e)}")

    async def connect_stdio_async(self, server_url: str) -> None:
        self._server_name = server_url

        try:
            from mcp.client.stdio import stdio_client
            from mcp import ClientSession
            from mcp import StdioServerParameters

            cmd = server_url[6:].split()
            # Pass the current environment to the subprocess
            server_params = StdioServerParameters(
                command=cmd[0], args=cmd[1:], env=os.environ.copy()
            )

            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    response = await session.list_tools()

                    # Convert list of tool objects to {name: {description: ...}}
                    tools_dict = {
                        tool.name: {"description": getattr(tool, "description", "")}
                        for tool in response.tools
                        if hasattr(tool, "name")
                    }
                    self._available_tools = self._parse_tools(tools_dict)

        except asyncio.TimeoutError as e:
            raise RailLockError("Connection to stdio server timed out")
        except Exception as e:
            raise RailLockError(
                f"Failed to communicate with stdio process (async): {str(e)}"
            )

    def close(self) -> None:
        """Close the connection to the server."""
        if self._process:
            self._process.terminate()
            self._process = None

    def _parse_tools(self, tools_data: dict) -> Dict[str, dict]:
        """Parse and validate the tools data from the server."""
        if not isinstance(tools_data, dict):
            raise RailLockError("Invalid tools data format")

        parsed_tools = {}
        for tool_name, tool_info in tools_data.items():
            if not isinstance(tool_info, dict):
                continue

            if "description" not in tool_info:
                continue

            parsed_tools[tool_name] = {
                "description": tool_info["description"],
                "checksum": self._calculate_checksum(
                    tool_name, tool_info["description"]
                ),
            }

        return parsed_tools

    def _is_tool_allowed(self, tool_name: str, tool_data: dict) -> bool:
        if tool_name not in self.config.allowed_tools:
            return False
        allowed_val = self.config.allowed_tools[tool_name]
        if isinstance(allowed_val, dict):
            expected_checksum = allowed_val["checksum"]
            server_name = allowed_val.get("server", self._server_name)
        else:
            expected_checksum = allowed_val
            server_name = self._server_name
        actual_checksum = calculate_tool_checksum(
            tool_name, tool_data["description"], server_name
        )
        return actual_checksum == expected_checksum

    def _calculate_checksum(self, tool_name: str, description: str) -> str:
        """Calculate the checksum for a tool."""
        return calculate_tool_checksum(tool_name, description, self._server_name)

    def filter_tools(self, tools):
        allowed = set(self.config.allowed_tools)
        malicious = set(self.config.malicious_tools)
        denied = set(self.config.denied_tools)
        filtered = []
        for tool in tools:
            name = getattr(tool, "name", None)
            desc = getattr(tool, "description", "")
            checksum = getattr(tool, "checksum", "")
            is_allowed = name in allowed
            is_malicious = name in malicious
            is_denied = name in denied
            checksum_ok = self._is_tool_allowed(
                name, {"description": desc, "checksum": checksum}
            )
            if is_allowed and not is_malicious and not is_denied and checksum_ok:
                filtered.append(tool)
        return filtered

    def test_server(self, server_url: str, timeout: int = 5) -> bool:
        """Test if the server is up and running before connecting."""
        if server_url.startswith("stdio:"):
            import shutil

            cmd = server_url[6:].split()[0]
            if shutil.which(cmd) is None:
                raise RailLockError(f"STDIO server executable not found: {cmd}")
            return True
        else:
            from urllib.parse import urlparse
            import requests

            parsed_url = urlparse(server_url)
            if parsed_url.scheme not in ["http", "https"]:
                raise RailLockError(f"Invalid server URL scheme: {parsed_url.scheme}")
            try:
                # Try HEAD first, fallback to GET if not supported
                try:
                    resp = requests.head(server_url, timeout=timeout)
                    if resp.status_code == 405:
                        resp = requests.get(server_url, timeout=timeout)
                except requests.RequestException:
                    resp = requests.get(server_url, timeout=timeout)
                if resp.status_code >= 400:
                    raise RailLockError(
                        f"Server responded with error code: {resp.status_code}"
                    )
                return True
            except requests.RequestException as e:
                raise RailLockError(f"Failed to reach server: {e}")
