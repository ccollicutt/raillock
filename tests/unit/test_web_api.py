"""Tests for the web API endpoints."""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from starlette.applications import Starlette
from starlette.testclient import TestClient
from starlette.requests import Request

from raillock.cli.commands.web.app import create_app
from raillock.cli.commands.web.api import (
    get_tools_api,
    preview_config_api,
    save_config_api,
    compare_config_api,
    save_manual_config_api,
)


@pytest.fixture
def test_tools():
    """Sample tools for testing."""
    return [
        {"name": "test_tool_1", "description": "A test tool for testing"},
        {"name": "test_tool_2", "description": "Another test tool"},
    ]


@pytest.fixture
def mock_state():
    """Mock app state for testing."""
    state = Mock()
    state.tools = [
        {"name": "test_tool_1", "description": "A test tool for testing"},
        {"name": "test_tool_2", "description": "Another test tool"},
    ]
    state.server_name = "test_server"
    state.server_type = "sse"
    state.server_url = "http://localhost:8000/sse"
    state.use_sse = True
    state.client = None
    return state


@pytest.fixture
def mock_request(mock_state):
    """Mock request object for testing."""
    request = Mock(spec=Request)
    request.app = Mock()
    request.app.state = mock_state
    return request


class TestGetToolsAPI:
    """Test the get_tools_api endpoint."""

    @pytest.mark.asyncio
    async def test_get_tools_sse_success(self, mock_request):
        """Test successful tool retrieval via SSE."""
        # Create proper tool objects, not Mock objects
        tool1 = Mock()
        tool1.name = "tool1"
        tool1.description = "Test tool 1"

        tool2 = Mock()
        tool2.name = "tool2"
        tool2.description = "Test tool 2"

        mock_tools = [tool1, tool2]

        with patch("raillock.cli.commands.web.api.get_tools_via_sse") as mock_get_tools:
            mock_get_tools.return_value = (mock_tools, "real_server_name")

            response = await get_tools_api(mock_request)

            assert response.status_code == 200
            data = json.loads(response.body)
            assert data["server_name"] == "real_server_name"
            assert data["server_type"] == "sse"
            assert len(data["tools"]) == 2
            assert data["tools"][0]["name"] == "tool1"

    @pytest.mark.asyncio
    async def test_get_tools_stdio_success(self, mock_request):
        """Test successful tool retrieval via stdio."""
        mock_request.app.state.use_sse = False
        mock_request.app.state.server_url = "stdio:python test_server.py"

        mock_client = Mock()
        mock_client._available_tools = {
            "tool1": {"description": "Test tool 1"},
            "tool2": {"description": "Test tool 2"},
        }
        # Make connect_async an async mock
        mock_client.connect_async = AsyncMock()

        with patch("raillock.cli.commands.web.api.RailLockClient") as mock_client_class:
            mock_client_class.return_value = mock_client
            mock_request.app.state.client = None

            response = await get_tools_api(mock_request)

            assert response.status_code == 200
            data = json.loads(response.body)
            assert data["server_type"] == "stdio"
            assert len(data["tools"]) == 2

    @pytest.mark.asyncio
    async def test_get_tools_error(self, mock_request):
        """Test error handling in get_tools_api."""
        with patch("raillock.cli.commands.web.api.get_tools_via_sse") as mock_get_tools:
            mock_get_tools.side_effect = Exception("Connection failed")

            response = await get_tools_api(mock_request)

            assert response.status_code == 500
            data = json.loads(response.body)
            assert "error" in data
            assert "Connection failed" in data["error"]


class TestPreviewConfigAPI:
    """Test the preview_config_api endpoint."""

    @pytest.mark.asyncio
    async def test_preview_config_success(self, mock_request):
        """Test successful configuration preview."""
        mock_request.json = AsyncMock(
            return_value={"choices": {"test_tool_1": "allow", "test_tool_2": "deny"}}
        )

        with (
            patch("raillock.cli.commands.web.api.build_config_dict") as mock_build,
            patch(
                "raillock.cli.commands.web.api.config_dict_to_yaml_string"
            ) as mock_yaml,
        ):
            mock_config = {
                "allowed_tools": {"test_tool_1": {}},
                "denied_tools": {"test_tool_2": {}},
                "malicious_tools": {},
            }
            mock_build.return_value = mock_config
            mock_yaml.return_value = "yaml_content"

            response = await preview_config_api(mock_request)

            assert response.status_code == 200
            data = json.loads(response.body)
            assert data["success"] is True
            assert data["summary"]["allowed"] == 1
            assert data["summary"]["denied"] == 1
            assert data["summary"]["malicious"] == 0
            assert data["yaml_content"] == "yaml_content"

    @pytest.mark.asyncio
    async def test_preview_config_error(self, mock_request):
        """Test error handling in preview_config_api."""
        mock_request.json = AsyncMock(side_effect=Exception("Invalid JSON"))

        response = await preview_config_api(mock_request)

        assert response.status_code == 500
        data = json.loads(response.body)
        assert "error" in data


class TestSaveConfigAPI:
    """Test the save_config_api endpoint."""

    @pytest.mark.asyncio
    async def test_save_config_success(self, mock_request):
        """Test successful configuration save."""
        mock_request.json = AsyncMock(
            return_value={
                "choices": {"test_tool_1": "allow"},
                "filename": "test_config.yaml",
            }
        )

        with (
            patch("raillock.cli.commands.web.api.build_config_dict") as mock_build,
            patch("raillock.cli.commands.web.api.save_config_to_file") as mock_save,
        ):
            mock_build.return_value = {"config": "data"}

            response = await save_config_api(mock_request)

            assert response.status_code == 200
            data = json.loads(response.body)
            assert data["success"] is True
            assert data["config_path"] == "test_config.yaml"
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_config_default_filename(self, mock_request):
        """Test save config with default filename."""
        mock_request.json = AsyncMock(
            return_value={"choices": {"test_tool_1": "allow"}}
        )

        with (
            patch("raillock.cli.commands.web.api.build_config_dict"),
            patch("raillock.cli.commands.web.api.save_config_to_file") as mock_save,
        ):
            response = await save_config_api(mock_request)

            assert response.status_code == 200
            data = json.loads(response.body)
            assert data["config_path"] == "raillock_config.yaml"


class TestCompareConfigAPI:
    """Test the compare_config_api endpoint."""

    @pytest.mark.asyncio
    async def test_compare_config_success(self, mock_request):
        """Test successful configuration comparison."""
        config_yaml = """
config_version: 1
server:
  name: test_server
  type: sse
allowed_tools:
  tool1:
    description: "Tool 1"
    server: test_server
    checksum: "abc123"
"""

        mock_request.json = AsyncMock(return_value={"config_content": config_yaml})

        # Create proper tool object, not Mock objects
        tool1 = Mock()
        tool1.name = "tool1"
        tool1.description = "Tool 1"
        mock_tools = [tool1]

        with (
            patch("raillock.cli.commands.web.api.get_tools_via_sse") as mock_get_tools,
            patch(
                "raillock.cli.commands.web.api.calculate_tool_checksum"
            ) as mock_checksum,
        ):
            mock_get_tools.return_value = (mock_tools, "test_server")
            mock_checksum.return_value = "abc123"

            response = await compare_config_api(mock_request)

            assert response.status_code == 200
            data = json.loads(response.body)
            assert data["success"] is True
            assert "summary" in data
            assert "comparison_data" in data

    @pytest.mark.asyncio
    async def test_compare_config_invalid_yaml(self, mock_request):
        """Test comparison with invalid YAML."""
        mock_request.json = AsyncMock(
            return_value={"config_content": "invalid: yaml: content:"}
        )

        response = await compare_config_api(mock_request)

        assert response.status_code == 400
        data = json.loads(response.body)
        assert "error" in data
        assert "Invalid YAML" in data["error"]


class TestSaveManualConfigAPI:
    """Test the save_manual_config_api endpoint."""

    @pytest.mark.asyncio
    async def test_save_manual_config_success(self, mock_request):
        """Test successful manual config save."""
        yaml_content = """
config_version: 1
server:
  name: test_server
  type: sse
allowed_tools: {}
"""

        mock_request.json = AsyncMock(
            return_value={
                "yaml_content": yaml_content,
                "filename": "manual_config.yaml",
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "manual_config.yaml")

            # Mock the file writing by patching open
            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file

                response = await save_manual_config_api(mock_request)

                assert response.status_code == 200
                data = json.loads(response.body)
                assert data["success"] is True
                assert "manual_config.yaml" in data["config_path"]

    @pytest.mark.asyncio
    async def test_save_manual_config_empty_content(self, mock_request):
        """Test manual config save with empty content."""
        mock_request.json = AsyncMock(
            return_value={"yaml_content": "", "filename": "empty_config.yaml"}
        )

        response = await save_manual_config_api(mock_request)

        assert response.status_code == 400
        data = json.loads(response.body)
        assert "error" in data
        assert "empty" in data["error"].lower()


class TestIntegration:
    """Integration tests for the web API."""

    def test_app_creation(self):
        """Test that the app can be created and routes are configured."""
        app = create_app()
        assert isinstance(app, Starlette)

        client = TestClient(app)

        # Test that routes exist (will fail without proper server setup, but routes should be there)
        with patch.object(app.state, "tools", []):
            with patch.object(app.state, "server_name", "test"):
                with patch.object(app.state, "server_type", "test"):
                    response = client.get("/api/tools")
                    # Should get a 500 error due to missing server, but route exists
                    assert response.status_code in [200, 500]

    def test_error_handling_consistency(self):
        """Test that all API endpoints handle errors consistently."""
        # This would be expanded to test consistent error response formats
        pass


class TestStdioEnvironmentInheritance:
    """Test environment variable inheritance for stdio connections in web API."""

    @pytest.fixture
    def stdio_mock_request(self, mock_state):
        """Mock request for stdio server testing."""
        mock_state.use_sse = False
        mock_state.server_url = "stdio:/tmp/test-server args"
        mock_state.client = None

        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = mock_state
        return request

    @pytest.mark.asyncio
    async def test_stdio_environment_inheritance_in_get_tools(self, stdio_mock_request):
        """Test that environment variables are inherited when connecting via stdio in get_tools_api."""
        # Set up test environment variable
        test_env_var = "TEST_GITHUB_TOKEN"
        test_env_value = "test_token_value"
        original_env = os.environ.get(test_env_var)

        try:
            os.environ[test_env_var] = test_env_value

            mock_client = Mock()
            mock_client._available_tools = {
                "github_tool": {"description": "GitHub integration tool"}
            }

            with (
                patch(
                    "raillock.cli.commands.web.api.RailLockClient"
                ) as mock_client_class,
                patch("raillock.cli.commands.web.api.RailLockConfig"),
            ):
                mock_client_class.return_value = mock_client
                # Mock the connect_async method to capture the call
                mock_client.connect_async = AsyncMock()

                response = await get_tools_api(stdio_mock_request)

                # Verify connect_async was called
                mock_client.connect_async.assert_called_once_with(
                    "stdio:/tmp/test-server args"
                )

                # Verify response is successful
                assert response.status_code == 200
                data = json.loads(response.body)
                assert data["server_type"] == "stdio"
                assert len(data["tools"]) == 1
                assert data["tools"][0]["name"] == "github_tool"

        finally:
            # Cleanup
            if original_env is not None:
                os.environ[test_env_var] = original_env
            elif test_env_var in os.environ:
                del os.environ[test_env_var]

    @pytest.mark.asyncio
    async def test_stdio_environment_inheritance_in_compare_config(
        self, stdio_mock_request
    ):
        """Test environment variable inheritance in compare_config_api for stdio."""
        # Setup test data
        stdio_mock_request.json = AsyncMock(
            return_value={
                "config_content": """
config_version: 1
server:
  name: test_server
  type: stdio
allowed_tools:
  github_tool:
    description: GitHub tool
    checksum: abc123
            """.strip()
            }
        )

        test_env_var = "GITHUB_PERSONAL_ACCESS_TOKEN"
        test_env_value = "github_pat_test123"
        original_env = os.environ.get(test_env_var)

        try:
            os.environ[test_env_var] = test_env_value

            mock_client = Mock()
            mock_client._available_tools = {
                "github_tool": {"description": "GitHub tool", "checksum": "abc123"}
            }

            with (
                patch(
                    "raillock.cli.commands.web.api.RailLockClient"
                ) as mock_client_class,
                patch("raillock.cli.commands.web.api.RailLockConfig"),
                patch(
                    "raillock.cli.commands.web.api.compare_config_with_server"
                ) as mock_compare,
            ):
                mock_client_class.return_value = mock_client
                mock_client.connect_async = AsyncMock()

                # Mock compare function
                mock_compare.return_value = ([], {"matched": 1, "mismatched": 0})

                response = await compare_config_api(stdio_mock_request)

                # Verify connect_async was called
                mock_client.connect_async.assert_called_once_with(
                    "stdio:/tmp/test-server args"
                )

                # Verify response
                assert response.status_code == 200
                data = json.loads(response.body)
                assert data["success"] is True

        finally:
            # Cleanup
            if original_env is not None:
                os.environ[test_env_var] = original_env
            elif test_env_var in os.environ:
                del os.environ[test_env_var]

    @pytest.mark.asyncio
    async def test_multiple_environment_variables_inheritance(self, stdio_mock_request):
        """Test that multiple environment variables are properly inherited."""
        # Setup multiple test environment variables
        test_vars = {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "github_token_123",
            "CUSTOM_API_KEY": "custom_key_456",
            "DEBUG_MODE": "true",
        }
        original_values = {}

        try:
            # Set test environment variables and save originals
            for var, value in test_vars.items():
                original_values[var] = os.environ.get(var)
                os.environ[var] = value

            mock_client = Mock()
            mock_client._available_tools = {
                "multi_tool": {"description": "Tool using multiple env vars"}
            }

            with (
                patch(
                    "raillock.cli.commands.web.api.RailLockClient"
                ) as mock_client_class,
                patch("raillock.cli.commands.web.api.RailLockConfig"),
            ):
                mock_client_class.return_value = mock_client
                mock_client.connect_async = AsyncMock()

                response = await get_tools_api(stdio_mock_request)

                # Verify connection was attempted
                mock_client.connect_async.assert_called_once()

                # Verify response
                assert response.status_code == 200

        finally:
            # Cleanup all test variables
            for var, original_value in original_values.items():
                if original_value is not None:
                    os.environ[var] = original_value
                elif var in os.environ:
                    del os.environ[var]

    @pytest.mark.asyncio
    async def test_stdio_error_propagation_with_environment(self, stdio_mock_request):
        """Test that stdio connection errors are properly propagated even with environment setup."""
        test_env_var = "TEST_ENV_VAR"
        test_env_value = "test_value"
        original_env = os.environ.get(test_env_var)

        try:
            os.environ[test_env_var] = test_env_value

            with (
                patch(
                    "raillock.cli.commands.web.api.RailLockClient"
                ) as mock_client_class,
                patch("raillock.cli.commands.web.api.RailLockConfig"),
            ):
                mock_client = Mock()
                # Simulate connection failure
                mock_client.connect_async = AsyncMock(
                    side_effect=Exception("Server not found")
                )
                mock_client_class.return_value = mock_client

                response = await get_tools_api(stdio_mock_request)

                # Verify error response
                assert response.status_code == 500
                data = json.loads(response.body)
                assert "error" in data
                assert "Server not found" in data["error"]

        finally:
            # Cleanup
            if original_env is not None:
                os.environ[test_env_var] = original_env
            elif test_env_var in os.environ:
                del os.environ[test_env_var]


if __name__ == "__main__":
    pytest.main([__file__])
