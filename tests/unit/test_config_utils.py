"""Tests for the config utilities module."""

import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)
import pytest
import tempfile
import os
import yaml
from unittest.mock import patch, Mock

from raillock.config_utils import (
    build_config_dict,
    get_yaml_str_presenter,
    save_config_to_file,
    config_dict_to_yaml_string,
)


class TestBuildConfigDict:
    """Test the build_config_dict function."""

    def test_build_config_dict_with_choices(self):
        """Test building config dict with various choices."""
        tools = [
            {"name": "tool1", "description": "Test tool 1"},
            {"name": "tool2", "description": "Test tool 2"},
            {"name": "tool3", "description": "Test tool 3"},
        ]
        choices = {"tool1": "allow", "tool2": "deny", "tool3": "malicious"}

        with patch("raillock.utils.calculate_tool_checksum") as mock_checksum:
            mock_checksum.return_value = "test_checksum"

            result = build_config_dict(tools, choices, "test_server", "sse")

            assert result["config_version"] == 1
            assert result["server"]["name"] == "test_server"
            assert result["server"]["type"] == "sse"

            assert "tool1" in result["allowed_tools"]
            assert "tool2" in result["denied_tools"]
            assert "tool3" in result["malicious_tools"]

            assert result["allowed_tools"]["tool1"]["description"] == "Test tool 1"
            assert result["allowed_tools"]["tool1"]["checksum"] == "test_checksum"

    def test_build_config_dict_with_object_tools(self):
        """Test building config dict with tool objects instead of dicts."""
        tool1 = Mock()
        tool1.name = "tool1"
        tool1.description = "Test tool 1"

        tool2 = Mock()
        tool2.name = "tool2"
        tool2.description = "Test tool 2"

        tools = [tool1, tool2]
        choices = {"tool1": "allow", "tool2": "deny"}

        with patch("raillock.utils.calculate_tool_checksum") as mock_checksum:
            mock_checksum.return_value = "test_checksum"

            result = build_config_dict(tools, choices, "test_server", "stdio")

            assert "tool1" in result["allowed_tools"]
            assert "tool2" in result["denied_tools"]
            assert result["server"]["type"] == "stdio"

    def test_build_config_dict_no_choices(self):
        """Test building config dict with no choices made."""
        tools = [
            {"name": "tool1", "description": "Test tool 1"},
            {"name": "tool2", "description": "Test tool 2"},
        ]
        choices = {}

        result = build_config_dict(tools, choices, "test_server", "http")

        assert len(result["allowed_tools"]) == 0
        assert len(result["denied_tools"]) == 0
        assert len(result["malicious_tools"]) == 0

    def test_build_config_dict_dedents_descriptions(self):
        """Test that descriptions are properly dedented."""
        tools = [
            {
                "name": "tool1",
                "description": "    Indented description\n    with multiple lines",
            },
        ]
        choices = {"tool1": "allow"}

        with patch("raillock.utils.calculate_tool_checksum") as mock_checksum:
            mock_checksum.return_value = "test_checksum"

            result = build_config_dict(tools, choices, "test_server", "sse")

            desc = result["allowed_tools"]["tool1"]["description"]
            assert not desc.startswith("    ")
            assert "Indented description" in desc


class TestYAMLUtilities:
    """Test YAML-related utility functions."""

    def test_get_yaml_str_presenter(self):
        """Test the YAML string presenter function."""
        presenter = get_yaml_str_presenter()

        # Create a mock dumper
        dumper = Mock()
        dumper.represent_scalar = Mock(return_value=Mock())

        # Test multi-line string
        result = presenter(dumper, "line1\nline2")
        dumper.represent_scalar.assert_called_with(
            "tag:yaml.org,2002:str", "line1\nline2", style="|"
        )

        # Test string with special characters
        dumper.represent_scalar.reset_mock()
        result = presenter(dumper, "test: value")
        dumper.represent_scalar.assert_called_with(
            "tag:yaml.org,2002:str", "test: value", style='"'
        )

        # Test normal string
        dumper.represent_scalar.reset_mock()
        result = presenter(dumper, "normal_string")
        dumper.represent_scalar.assert_called_with(
            "tag:yaml.org,2002:str", "normal_string"
        )

    def test_config_dict_to_yaml_string(self):
        """Test converting config dict to YAML string."""
        config_dict = {
            "config_version": 1,
            "server": {"name": "test", "type": "sse"},
            "allowed_tools": {},
        }

        result = config_dict_to_yaml_string(config_dict)

        assert "config_version: 1" in result
        assert "name: test" in result
        assert "type: sse" in result

    def test_save_config_to_file(self):
        """Test saving config to file."""
        config_dict = {
            "config_version": 1,
            "server": {"name": "test", "type": "sse"},
            "allowed_tools": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test_config")

            save_config_to_file(config_dict, filename)

            # Check that .yaml extension was added
            expected_file = filename + ".yaml"
            assert os.path.exists(expected_file)

            # Check file contents
            with open(expected_file, "r") as f:
                content = f.read()
                assert "config_version: 1" in content

    def test_save_config_to_file_with_extension(self):
        """Test saving config to file that already has extension."""
        config_dict = {"config_version": 1}

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test_config.yaml")

            save_config_to_file(config_dict, filename)

            # Should not add another extension
            assert os.path.exists(filename)
            assert not os.path.exists(filename + ".yaml")


if __name__ == "__main__":
    pytest.main([__file__])
