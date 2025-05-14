"""
Utilities for integrating RailLock with MCP ClientSession.

- RailLockSessionWrapper: Use as a drop-in replacement for session to always apply RailLock filtering and custom logic to tool lists.
- monkeypatch_raillock_tools: Monkeypatches ClientSession.list_tools to always apply RailLock filtering and custom logic globally for that session instance.

Choose the approach that best fits your use case:
- Use RailLockSessionWrapper for explicit, per-instance control.
- Use monkeypatch_raillock_tools for global, behind-the-scenes enforcement (e.g., for third-party code or multiple models).
"""

import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
import logging
from raillock.exceptions import RailLockError
from urllib.parse import urlparse


def monkeypatch_raillock_tools(session, rail_client):
    """
    Monkeypatch the session's list_tools method to always apply RailLock filtering and inject default descriptions.
    After calling this, any call to session.list_tools() will use RailLock logic.
    Args:
        session: An MCP ClientSession instance.
        rail_client: A RailLockClient instance.
    """
    original_list_tools = session.list_tools

    async def patched_list_tools(*args, **kwargs):
        response = await original_list_tools(*args, **kwargs)
        tools = rail_client.filter_tools(response.tools)
        logging.debug(
            f"[RailLockMonkeypatch] Filtered tools: {[tool.name for tool in tools]}"
        )
        for tool in tools:
            if not getattr(tool, "description", None):
                logging.debug(
                    f"[RailLockMonkeypatch] Injecting default description for tool: {tool.name}"
                )
                tool.description = "No description provided (client override)"

        # Return a response-like object with .tools attribute for compatibility
        class _FakeResponse:
            def __init__(self, tools):
                self.tools = tools

        return _FakeResponse(tools)

    session.list_tools = patched_list_tools


def get_server_name_from_session(session):
    """
    Try to fetch the server name from the MCP session after initialization.
    Returns the server name as a string, or None if not available.
    """
    # Try common attributes (update as needed for your MCP SDK)
    return (
        getattr(session, "server_name", None) or getattr(session, "name", None) or None
    )


async def get_tools_via_sse(server_url):
    """
    Connect to an MCP SSE server, perform the handshake, and return the list of tools and server name.
    Args:
        server_url (str): The SSE endpoint URL (e.g., http://localhost:8000/sse)
    Returns:
        tuple: (list of tool objects, server name or None)
    """
    try:
        parsed = urlparse(server_url)
        if parsed.scheme not in ("http", "https"):
            raise RailLockError(f"Invalid server URL scheme: {parsed.scheme}")
        async with sse_client(server_url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                response = await session.list_tools()
                server_name = get_server_name_from_session(session)
                return response.tools, server_name
    except RailLockError:
        raise
    except (OSError, ConnectionRefusedError) as e:
        raise RailLockError(f"Failed to reach server: {e}")
    except Exception as e:
        msg = str(e)
        if "404" in msg:
            raise RailLockError("Failed to reach server: 404")
        if "connection refused" in msg.lower():
            raise RailLockError("Failed to reach server: connection refused")
        raise RailLockError(f"Failed to reach server: {e}")


class RailLockSessionWrapper:
    """
    Wrapper for MCP ClientSession that always applies RailLock filtering and custom logic to tool lists.
    Use as a drop-in replacement for session in your client code.
    """

    def __init__(self, session, rail_client):
        self.session = session
        self.rail_client = rail_client

    async def list_tools(self):
        response = await self.session.list_tools()
        tools = self.rail_client.filter_tools(response.tools)
        logging.debug(
            f"[RailLockSessionWrapper] Filtered tools: {[tool.name for tool in tools]}"
        )
        # Inject a default description if missing
        for tool in tools:
            if not getattr(tool, "description", None):
                logging.debug(
                    f"[RailLockSessionWrapper] Injecting default description for tool: {tool.name}"
                )
                tool.description = "No description provided (client override)"
        return tools
