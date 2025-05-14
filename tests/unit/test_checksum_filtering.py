import pytest
from raillock.client import RailLockClient
from raillock.config import RailLockConfig
from raillock.utils import calculate_tool_checksum


class DummyTool:
    def __init__(self, name, description):
        self.name = name
        self.description = description


def test_checksum_mismatch_filters_tool():
    """Test that a tool with a wrong checksum in config is filtered out (not allowed)."""
    name = "check_config"
    description = "Check the config of a file by reading the file."
    # Calculate the correct checksum as the server would
    correct_checksum = calculate_tool_checksum(name, description)
    # Use a deliberately wrong checksum in the config
    wrong_checksum = "deadbeef" * 8  # 64 hex chars, guaranteed wrong
    config = RailLockConfig(
        {name: {"description": description, "checksum": wrong_checksum}}
    )
    client = RailLockClient(config)
    # Simulate available tools from server
    client._available_tools = {
        name: {"description": description, "checksum": correct_checksum}
    }
    # Validate tools: should NOT include 'check_config'
    validated = client.validate_tools()
    assert name not in validated
    # Check is_tool_allowed directly
    assert not client._is_tool_allowed(
        name, {"description": description, "checksum": correct_checksum}
    )


def test_allowed_tool_with_correct_checksum_and_server_name():
    name = "echo"
    description = "Echo a string."
    server_name = "http://localhost:8000/sse"
    checksum = calculate_tool_checksum(name, description, server_name)
    config = RailLockConfig(
        {
            name: {
                "description": description,
                "checksum": checksum,
                "server": server_name,
            }
        }
    )
    client = RailLockClient(config)
    client._available_tools = {name: {"description": description, "checksum": checksum}}
    assert name in client.validate_tools()
    assert client._is_tool_allowed(
        name, {"description": description, "checksum": checksum}
    )


def test_allowed_tool_with_wrong_server_name():
    name = "echo"
    description = "Echo a string."
    server_name = "http://localhost:8000/sse"
    wrong_server_name = "http://localhost:9999/sse"
    checksum = calculate_tool_checksum(name, description, server_name)
    config = RailLockConfig(
        {
            name: {
                "description": description,
                "checksum": checksum,
                "server": wrong_server_name,
            }
        }
    )
    client = RailLockClient(config)
    client._available_tools = {name: {"description": description, "checksum": checksum}}
    assert name not in client.validate_tools()
    assert not client._is_tool_allowed(
        name, {"description": description, "checksum": checksum}
    )


def test_allowed_tool_stdio_protocol_ignores_server_name():
    name = "echo"
    description = "Echo a string."
    # For stdio, checksum should not use server_name
    checksum = calculate_tool_checksum(name, description)
    config = RailLockConfig({name: {"description": description, "checksum": checksum}})
    client = RailLockClient(config)
    client._available_tools = {name: {"description": description, "checksum": checksum}}
    assert name in client.validate_tools()
    assert client._is_tool_allowed(
        name, {"description": description, "checksum": checksum}
    )


def test_allowed_tool_in_denied_tools():
    name = "echo"
    description = "Echo a string."
    checksum = calculate_tool_checksum(name, description)
    config = RailLockConfig(
        allowed_tools={name: {"description": description, "checksum": checksum}},
        denied_tools={name: {"description": description, "checksum": checksum}},
    )
    client = RailLockClient(config)
    client._available_tools = {name: {"description": description, "checksum": checksum}}
    # Should not be allowed because it's denied
    assert name not in client.validate_tools()
    # But _is_tool_allowed will still return True (filter_tools/validate_tools enforce denied/malicious)


def test_allowed_tool_in_malicious_tools():
    name = "echo"
    description = "Echo a string."
    checksum = calculate_tool_checksum(name, description)
    config = RailLockConfig(
        allowed_tools={name: {"description": description, "checksum": checksum}},
        malicious_tools={name: {"description": description, "checksum": checksum}},
    )
    client = RailLockClient(config)
    client._available_tools = {name: {"description": description, "checksum": checksum}}
    # Should not be allowed because it's malicious
    assert name not in client.validate_tools()
    # But _is_tool_allowed will still return True (filter_tools/validate_tools enforce denied/malicious)
