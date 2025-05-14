import pytest
import requests
from unittest.mock import patch, MagicMock
from raillock.client import RailLockClient
from raillock.config import RailLockConfig
from raillock.exceptions import RailLockError
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


def test_validate_tools_and_is_tool_allowed():
    config = RailLockConfig({"echo": calculate_tool_checksum("echo", "desc")})
    client = RailLockClient(config)
    echo_checksum = calculate_tool_checksum("echo", "desc")
    add_checksum = calculate_tool_checksum("add", "desc")
    client._available_tools = {
        "echo": {"description": "desc", "checksum": echo_checksum},
        "add": {"description": "desc", "checksum": add_checksum},
    }
    validated = client.validate_tools()
    assert "echo" in validated
    assert "add" not in validated
    assert client._is_tool_allowed(
        "echo", {"description": "desc", "checksum": echo_checksum}
    )
    assert not client._is_tool_allowed(
        "add", {"description": "desc", "checksum": add_checksum}
    )


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


def test_validate_tools_empty():
    config = RailLockConfig()
    client = RailLockClient(config)
    client._available_tools = {}
    assert client.validate_tools() == {}


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


def test_checksum_matching():
    """Test that a tool with a matching checksum in config is recognized as allowed."""
    name = "echo"
    description = "desc"
    checksum = calculate_tool_checksum(name, description)
    config = RailLockConfig({name: checksum})
    client = RailLockClient(config)
    client._available_tools = {name: {"description": description, "checksum": checksum}}
    validated = client.validate_tools()
    assert name in validated
    assert client._is_tool_allowed(
        name, {"description": description, "checksum": checksum}
    )


def test_checksum_not_matching():
    """Test that a tool with a non-matching checksum in config is not recognized as allowed."""
    name = "echo"
    description = "desc"
    checksum = calculate_tool_checksum(name, description)
    wrong_checksum = "0" * 64
    config = RailLockConfig({name: wrong_checksum})
    client = RailLockClient(config)
    client._available_tools = {name: {"description": description, "checksum": checksum}}
    validated = client.validate_tools()
    assert name not in validated
    assert not client._is_tool_allowed(
        name, {"description": description, "checksum": checksum}
    )


def test_compare_logic_with_nested_config():
    """Test compare logic with a config file using nested dicts for allowed_tools."""
    # Simulate server tools
    server_tools = {
        "echo": {"description": "Echo the input text", "checksum": "abc123"},
        "add": {"description": "Add two integers", "checksum": "def456"},
        "delete_folder": {"description": "Delete a folder", "checksum": "ghi789"},
    }
    # Simulate config allowed_tools in nested dict format
    allowed_tools = {
        "echo": {"description": "Echo the input text", "checksum": "abc123"},
        "add": {"description": "Add two integers", "checksum": "wrong"},
    }

    # Compare logic
    def check(v):
        return "✔" if v else "✘"

    results = []
    for tool in sorted(set(server_tools.keys()) | set(allowed_tools.keys())):
        on_server = tool in server_tools
        allowed = tool in allowed_tools
        allowed_checksum = None
        if allowed:
            allowed_val = allowed_tools[tool]
            if isinstance(allowed_val, dict) and "checksum" in allowed_val:
                allowed_checksum = allowed_val["checksum"]
            elif isinstance(allowed_val, str):
                allowed_checksum = allowed_val
        server_checksum = server_tools[tool]["checksum"] if on_server else None
        checksum_match = (
            on_server
            and allowed
            and allowed_checksum is not None
            and server_checksum == allowed_checksum
        )
        results.append((tool, check(on_server), check(allowed), check(checksum_match)))
    # echo should match, add should not, delete_folder should not be allowed
    assert results[0][0] == "add" and results[0][3] == "✘"
    assert results[1][0] == "delete_folder" and results[1][3] == "✘"
    assert results[2][0] == "echo" and results[2][3] == "✔"


def test_malicious_overrides_allowed():
    config = RailLockConfig(
        allowed_tools={"echo": {"description": "desc", "checksum": "abc"}},
        malicious_tools={"echo": {"description": "desc", "checksum": "abc"}},
    )
    client = RailLockClient(config)
    # Simulate available tools
    client._available_tools = {"echo": {"description": "desc", "checksum": "abc"}}
    # Should not be allowed because it's also malicious
    validated = client.validate_tools()
    assert "echo" not in validated

    # Also test filter_tools
    class Tool:
        def __init__(self, name):
            self.name = name

    filtered = client.filter_tools([Tool("echo")])
    assert filtered == []
