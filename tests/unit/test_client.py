import pytest
import requests
from unittest.mock import patch, MagicMock, AsyncMock
from raillock.client import RailLockClient
from raillock.config import RailLockConfig
from raillock.exceptions import RailLockError
from raillock.config_utils import compare_config_with_server
import json
import shutil
import os
from raillock.utils import calculate_tool_checksum


try:
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from mcp.types import JSONRPCMessage, JSONRPCRequest, JSONRPCResponse
    import pytest
    import shutil

    tee: str = shutil.which("tee")
    HAVE_MCP_SDK = True
except ImportError:
    HAVE_MCP_SDK = False
    tee = None


class DummyTool:
    def __init__(self, name, description="desc"):
        self.name = name
        self.description = description


def test_raillock_client_filter_tools():
    config = RailLockConfig(
        {
            "echo": calculate_tool_checksum("echo", "desc"),
            "add": calculate_tool_checksum("add", "desc"),
        }
    )
    client = RailLockClient(config)
    tools = [
        DummyTool("echo", "desc"),
        DummyTool("add", "desc"),
        DummyTool("not_allowed", "desc"),
    ]
    # Simulate server tool dicts with correct checksums
    for t in tools:
        t.checksum = calculate_tool_checksum(t.name, t.description)
    filtered = client.filter_tools(tools)
    filtered_names = [t.name for t in filtered]
    assert "echo" in filtered_names
    assert "add" in filtered_names
    assert "not_allowed" not in filtered_names


def test_parse_tools_and_calculate_checksum():
    config = RailLockConfig()
    client = RailLockClient(config)
    tools_data = {"echo": {"description": "desc"}, "add": {"description": "desc"}}
    parsed = client._parse_tools(tools_data)
    assert "echo" in parsed
    assert "add" in parsed
    checksum = client._calculate_checksum("echo", "desc")
    assert isinstance(checksum, str) and len(checksum) == 64


def test_parse_tools_invalid_format():
    config = RailLockConfig()
    client = RailLockClient(config)
    with pytest.raises(Exception):
        client._parse_tools([1, 2, 3])
    # Should skip non-dict tool info
    assert client._parse_tools({"bad": "notadict"}) == {}


@patch("requests.get")
def test_connect_http_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"echo": {"description": "desc"}}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    client = RailLockClient(RailLockConfig())
    client.connect("http://testserver")
    mock_get.assert_called_once_with("http://testserver", timeout=10)
    assert "echo" in client._available_tools


@patch("requests.get")
def test_connect_http_request_error(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Network error")
    client = RailLockClient(RailLockConfig())
    with pytest.raises(RailLockError, match="Failed to connect"):
        client.connect("http://testserver")


@patch("requests.get")
def test_connect_http_bad_json(mock_get):
    mock_response = MagicMock()
    mock_response.json.side_effect = json.JSONDecodeError("bad json", "", 0)
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    client = RailLockClient(RailLockConfig())
    with pytest.raises(RailLockError, match="Invalid response format"):
        client.connect("http://testserver")


def test_connect_invalid_scheme():
    client = RailLockClient(RailLockConfig())
    with pytest.raises(
        RailLockError,
        match="Invalid server URL scheme: stio.*Use stdio: for subprocess, or http\(s\):// for network servers.",
    ):
        client.connect("stio://testserver")


def test_close_no_process():
    client = RailLockClient(RailLockConfig())
    client.close()  # Should not raise error


echo_server = os.path.abspath("examples/most-basic/echo_server.py")
is_executable = os.path.isfile(echo_server) and os.access(echo_server, os.X_OK)

if HAVE_MCP_SDK:

    @pytest.mark.anyio
    @pytest.mark.skipif(tee is None, reason="could not find tee command")
    async def test_sdk_style_stdio_client():
        server_parameters = StdioServerParameters(command=tee)
        async with stdio_client(server_parameters) as (read_stream, write_stream):
            messages = [
                JSONRPCMessage(root=JSONRPCRequest(jsonrpc="2.0", id=1, method="ping")),
                JSONRPCMessage(root=JSONRPCResponse(jsonrpc="2.0", id=2, result={})),
            ]
            async with write_stream:
                for message in messages:
                    await write_stream.send(message)
            read_messages = []
            async with read_stream:
                async for message in read_stream:
                    if isinstance(message, Exception):
                        raise message
                    read_messages.append(message)
                    if len(read_messages) == 2:
                        break
            assert len(read_messages) == 2
            assert read_messages[0] == JSONRPCMessage(
                root=JSONRPCRequest(jsonrpc="2.0", id=1, method="ping")
            )
            assert read_messages[1] == JSONRPCMessage(
                root=JSONRPCResponse(jsonrpc="2.0", id=2, result={})
            )

    @pytest.mark.anyio
    @pytest.mark.skipif(not is_executable, reason="echo_server.py is not executable")
    async def test_sdk_style_real_stdio_server():
        from mcp import ClientSession

        server_parameters = StdioServerParameters(command="python", args=[echo_server])
        async with stdio_client(server_parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("[DEBUG] Session initialized (async)")
                response = await session.list_tools()
                print(f"[DEBUG] list_tools() response: {response}")
                for tool in response.tools:
                    print(
                        f"Tool: {tool.name}, Description: {getattr(tool, 'description', '')}"
                    )


def test_compare_logic_with_nested_config():
    """Test that the compare logic works properly with nested config structure."""
    # Create a simple config
    config_data = {
        "allowed_tools": {
            "echo": {
                "description": "Echo the input text",
                "checksum": "80ea71b3ef0597f02019c802bf49686f1152129686f087c4daadeafc1c606a68",
                "server": "http://testserver",
            }
        },
        "denied_tools": {},
    }

    # Server tools with matching checksums
    server_tools = {
        "echo": {
            "description": "Echo the input text",
            "checksum": "80ea71b3ef0597f02019c802bf49686f1152129686f087c4daadeafc1c606a68",
        },
    }

    # Compare config with server tools
    results, stats = compare_config_with_server(config_data, server_tools)

    # Should have results
    assert len(results) > 0

    # Should have echo tool that is allowed
    echo_result = next((r for r in results if r["tool"] == "echo"), None)
    assert echo_result is not None
    assert echo_result["type"] == "allowed"


def test_server_test_stdio_executable_check():
    """Test that test_server properly checks for stdio executable existence."""
    client = RailLockClient(RailLockConfig())

    # Test with existing executable
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/bin/echo"
        result = client.test_server("stdio:/bin/echo test")
        assert result is True
        mock_which.assert_called_once_with("/bin/echo")

    # Test with non-existing executable
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        with pytest.raises(RailLockError, match="STDIO server executable not found"):
            client.test_server("stdio:/nonexistent/command")
