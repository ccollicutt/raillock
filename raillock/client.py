"""
RailLockClient - Core client class for MCP server communication and tool validation.
"""

import hashlib
import json
import subprocess
from typing import Dict, Optional
from urllib.parse import urlparse
import asyncio

import requests
from requests.exceptions import RequestException

from .config import RailLockConfig
from .exceptions import RailLockError


class RailLockClient:
    """Client for connecting to MCP servers and validating tool access."""

    def __init__(self, config: RailLockConfig):
        """Initialize the client with a configuration."""
        self.config = config
        self._available_tools: Dict[str, dict] = {}
        self._validated_tools: Dict[str, dict] = {}
        self._process: Optional[subprocess.Popen] = None

    def connect(self, server_url: str) -> None:
        """Connect to an MCP server and fetch available tools."""
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
                print(f"[DEBUG] Sending GET request to {server_url}")
                response = requests.get(server_url, timeout=10)
                response.raise_for_status()
                tools_data = response.json()
                print(f"[DEBUG] Received tools data: {tools_data}")
                self._available_tools = self._parse_tools(tools_data)

        except RequestException as e:
            raise RailLockError(f"Failed to connect to server: {str(e)}")
        except json.JSONDecodeError:
            raise RailLockError("Invalid response format from server")
        except subprocess.SubprocessError as e:
            raise RailLockError(f"Failed to start stdio process: {str(e)}")

    async def connect_stdio_async(self, server_url: str) -> None:
        try:
            from mcp.client.stdio import stdio_client
            from mcp import ClientSession
            from mcp import StdioServerParameters

            cmd = server_url[6:].split()
            print(f"[DEBUG] Launching stdio server (async): {cmd}")
            server_params = StdioServerParameters(command=cmd[0], args=cmd[1:])
            async with stdio_client(server_params) as (read_stream, write_stream):
                print("[DEBUG] Opened stdio_client context (async)")
                async with ClientSession(read_stream, write_stream) as session:
                    print(
                        "[DEBUG] ClientSession context entered, initializing session (async)"
                    )
                    await session.initialize()
                    print("[DEBUG] Session initialized (async)")
                    response = await session.list_tools()
                    print(f"[DEBUG] list_tools() response: {response}")
                    # Convert list of tool objects to {name: {description: ...}}
                    tools_dict = {
                        tool.name: {"description": getattr(tool, "description", "")}
                        for tool in response.tools
                        if hasattr(tool, "name")
                    }
                    self._available_tools = self._parse_tools(tools_dict)
                    print(f"[DEBUG] Parsed tools: {self._available_tools}")
        except Exception as e:
            print(f"[DEBUG] Exception during async stdio connection: {e}")
            raise RailLockError(
                f"Failed to communicate with stdio process (async): {str(e)}"
            )

    def close(self) -> None:
        """Close the connection to the server."""
        if self._process:
            self._process.terminate()
            self._process = None

    def validate_tools(self) -> Dict[str, dict]:
        """Validate available tools against the configuration."""
        self._validated_tools = {}

        for tool_name, tool_data in self._available_tools.items():
            if self._is_tool_allowed(tool_name, tool_data):
                self._validated_tools[tool_name] = tool_data

        return self._validated_tools

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
        """Check if a tool is allowed based on the configuration."""
        if tool_name not in self.config.allowed_tools:
            return False

        expected_checksum = self.config.allowed_tools[tool_name]
        return tool_data["checksum"] == expected_checksum

    def _calculate_checksum(self, tool_name: str, description: str) -> str:
        """Calculate the checksum for a tool."""
        data = f"{tool_name}:{description}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def filter_tools(self, tools):
        """
        Return only tools allowed by the RailLock config.

        Args:
            tools (list): List of tool objects (must have .name attribute).

        Returns:
            list: Filtered list of allowed tool objects.
        """
        allowed = set(self.config.allowed_tools)
        return [tool for tool in tools if getattr(tool, "name", None) in allowed]

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
