import pytest
from raillock.mcp_utils import (
    RailLockSessionWrapper,
    monkeypatch_raillock_tools,
    get_server_name_from_session,
    get_tools_via_sse,
)
from raillock.config import RailLockConfig
from raillock.client import RailLockClient
from unittest.mock import patch, MagicMock, AsyncMock


class DummySession:
    async def list_tools(self):
        class Tool:
            def __init__(self, name, description=None):
                self.name = name
                self.description = description

        return type("Resp", (), {"tools": [Tool("echo", None), Tool("add", "desc")]})()


def test_raillock_session_wrapper_filters_and_injects():
    config = RailLockConfig({"echo": "*", "add": "*"})
    rail_client = RailLockClient(config)
    wrapper = RailLockSessionWrapper(DummySession(), rail_client)
    import asyncio

    tools = asyncio.run(wrapper.list_tools())
    names = [t.name for t in tools]
    assert "echo" in names
    assert "add" in names
    for t in tools:
        assert t.description is not None


def test_monkeypatch_raillock_tools():
    class DummySession:
        async def list_tools(self):
            class Tool:
                def __init__(self, name, description=None):
                    self.name = name
                    self.description = description

            return type(
                "Resp",
                (),
                {
                    "tools": [
                        Tool("echo", None),
                        Tool("add", "desc"),
                        Tool("not_allowed", None),
                    ]
                },
            )()

    config = RailLockConfig({"echo": "*", "add": "*"})
    rail_client = RailLockClient(config)
    session = DummySession()
    monkeypatch_raillock_tools(session, rail_client)
    import asyncio

    resp = asyncio.run(session.list_tools())
    names = [t.name for t in resp.tools]
    assert "echo" in names
    assert "add" in names
    assert "not_allowed" not in names
    for t in resp.tools:
        assert t.description is not None


def test_get_server_name_from_session():
    class S:
        server_name = "TestServer"

    assert get_server_name_from_session(S()) == "TestServer"

    class S2:
        name = "TestServer2"

    assert get_server_name_from_session(S2()) == "TestServer2"

    class S3:
        pass

    assert get_server_name_from_session(S3()) is None


@pytest.mark.anyio(backend="asyncio")
@patch("raillock.mcp_utils.sse_client")
@patch("raillock.mcp_utils.ClientSession")
async def test_get_tools_via_sse(mock_client_session, mock_sse_client):
    # Mock sse_client context manager
    mock_streams = (AsyncMock(), AsyncMock())
    mock_sse_client.return_value.__aenter__.return_value = mock_streams

    # Mock ClientSession context manager
    mock_session_instance = AsyncMock()
    mock_session_instance.initialize = AsyncMock()
    mock_session_instance.list_tools = AsyncMock()
    mock_session_instance.server_name = "TestServerFromSSE"

    class MockTool:
        name = "sse_tool"
        description = "sse desc"

    mock_session_instance.list_tools.return_value = type(
        "Resp", (), {"tools": [MockTool()]}
    )()
    mock_client_session.return_value.__aenter__.return_value = mock_session_instance

    tools, server_name = await get_tools_via_sse("http://sse-server")

    mock_sse_client.assert_called_once_with("http://sse-server")
    mock_client_session.assert_called_once_with(mock_streams[0], mock_streams[1])
    mock_session_instance.initialize.assert_called_once()
    mock_session_instance.list_tools.assert_called_once()
    assert server_name == "TestServerFromSSE"
    assert len(tools) == 1
    assert tools[0].name == "sse_tool"
