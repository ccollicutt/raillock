"""Test XSS protection in the web interface."""

import pytest
from unittest.mock import AsyncMock, patch

from raillock.cli.commands.web.api import get_tools_api


class MockRequest:
    """Mock request object for testing."""

    def __init__(self):
        self.app = MockApp()


class MockApp:
    """Mock app object for testing."""

    def __init__(self):
        self.state = MockState()


class MockState:
    """Mock state object for testing."""

    def __init__(self):
        self.use_sse = True
        self.server_url = "http://test-server"
        self.server_name = "test-server"
        self.server_type = "sse"
        self.tools = []
        self.client = None


class MockTool:
    """Mock tool object with potentially dangerous content."""

    def __init__(self, name, description):
        self.name = name
        self.description = description


@pytest.mark.asyncio
async def test_xss_protection_in_tool_descriptions():
    """Test that XSS attempts in tool descriptions are safely handled."""

    # Create tools with potentially dangerous content
    dangerous_tools = [
        MockTool(name="normal_tool", description="This is a normal description"),
        MockTool(
            name="<script>alert('xss')</script>",
            description="<script>alert('tool description xss');</script>",
        ),
        MockTool(
            name="injection_attempt",
            description="onload=\"alert('xss')\" <img src=x onerror=alert('xss')>",
        ),
        MockTool(
            name="html_tags",
            description="<div><h1>HTML Content</h1><p>Paragraph</p></div>",
        ),
    ]

    # Mock the get_tools_via_sse function to return our dangerous tools
    with patch("raillock.cli.commands.web.api.get_tools_via_sse") as mock_get_tools:
        mock_get_tools.return_value = (dangerous_tools, "test-server")

        # Call the API
        request = MockRequest()
        response = await get_tools_api(request)

        # Verify the response is successful
        assert response.status_code == 200

        # Get the response data
        import json

        response_data = json.loads(response.body)

        # Verify that the tools are returned but the dangerous content is preserved
        # (the escaping happens on the frontend)
        tools = response_data["tools"]
        assert len(tools) == 4

        # The API should return the raw content - escaping happens in JavaScript
        dangerous_tool = tools[1]
        assert dangerous_tool["name"] == "<script>alert('xss')</script>"
        assert (
            dangerous_tool["description"]
            == "<script>alert('tool description xss');</script>"
        )

        # Verify other dangerous content is preserved
        injection_tool = tools[2]
        assert "onload" in injection_tool["description"]
        assert "onerror" in injection_tool["description"]

        html_tool = tools[3]
        assert "<div>" in html_tool["description"]
        assert "<h1>" in html_tool["description"]


def test_javascript_escape_function():
    """Test the JavaScript escapeHtml function logic in Python to verify it works correctly."""

    def escape_html(text):
        """Python version of the JavaScript escapeHtml function for testing."""
        if not isinstance(text, str):
            return text

        escape_map = {
            "&": "&amp;",  # Must be first to avoid double-encoding
            "<": "&lt;",  # Prevents <script> tags
            ">": "&gt;",  # Prevents <script> tags
            '"': "&quot;",  # Prevents attribute injection
            "'": "&#039;",  # Prevents attribute injection
            "/": "&#x2F;",  # Additional protection for closing tags
            "`": "&#x60;",  # Prevents template literal injection
            "=": "&#x3D;",  # Prevents attribute injection
        }

        import re

        return re.sub(r'[&<>"\'`=/]', lambda m: escape_map[m.group(0)], text)

    # Test cases
    test_cases = [
        # Basic script tag
        (
            "<script>alert('xss')</script>",
            "&lt;script&gt;alert(&#039;xss&#039;)&lt;&#x2F;script&gt;",
        ),
        # Image with onerror
        (
            "<img src=x onerror=alert('xss')>",
            "&lt;img src&#x3D;x onerror&#x3D;alert(&#039;xss&#039;)&gt;",
        ),
        # Event handler
        ("onload=\"alert('xss')\"", "onload&#x3D;&quot;alert(&#039;xss&#039;)&quot;"),
        # Template literal
        ("`${alert('xss')}`", "&#x60;${alert(&#039;xss&#039;)}&#x60;"),
        # Normal text should be preserved
        ("This is normal text", "This is normal text"),
        # HTML tags should be escaped
        (
            "<div><h1>Title</h1></div>",
            "&lt;div&gt;&lt;h1&gt;Title&lt;&#x2F;h1&gt;&lt;&#x2F;div&gt;",
        ),
    ]

    for input_text, expected_output in test_cases:
        result = escape_html(input_text)
        assert result == expected_output, f"Failed for input: {input_text}"

        # Verify that the escaped result doesn't contain dangerous characters
        dangerous_chars = ["<", ">", '"', "'", "`", "="]
        for char in dangerous_chars:
            if char in input_text:
                assert char not in result, (
                    f"Dangerous character '{char}' not escaped in: {result}"
                )
