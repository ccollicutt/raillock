import yaml
import pytest
from raillock.config import RailLockConfig


def test_config_init_and_allowed_tools():
    config = RailLockConfig({"echo": "abc123"})
    assert config.allowed_tools["echo"] == "abc123"


def test_config_from_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("echo: abc123")
    config = RailLockConfig.from_file(str(config_path))
    assert config.allowed_tools["echo"] == "abc123"


def test_config_from_file_valid(tmp_path):
    config_data = {"echo": "abc123"}
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)
    config = RailLockConfig.from_file(str(config_file))
    assert config.allowed_tools == config_data


def test_config_from_file_missing(tmp_path):
    missing_file = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError):
        RailLockConfig.from_file(str(missing_file))


def test_config_from_file_invalid_yaml(tmp_path):
    bad_file = tmp_path / "bad.yaml"
    with open(bad_file, "w") as f:
        f.write(": not yaml")
    with pytest.raises(ValueError):
        RailLockConfig.from_file(str(bad_file))


def test_config_from_file_not_dict(tmp_path):
    bad_file = tmp_path / "bad2.yaml"
    with open(bad_file, "w") as f:
        yaml.safe_dump([1, 2, 3], f)
    with pytest.raises(ValueError):
        RailLockConfig.from_file(str(bad_file))


def test_config_from_file_nested_dict(tmp_path):
    config_data = {
        "config_version": 1,
        "server": {"name": "http://localhost:8000/sse", "type": "sse"},
        "allowed_tools": {
            "echo": {"description": "Echo the input text", "checksum": "abc123"},
            "add": {"description": "Add two integers", "checksum": "def456"},
        },
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)
    config = RailLockConfig.from_file(str(config_file))
    assert "echo" in config.allowed_tools
    assert config.allowed_tools["echo"]["checksum"] == "abc123"
    assert "add" in config.allowed_tools
    assert config.allowed_tools["add"]["checksum"] == "def456"


# Note: Config generation is now done via review --yes, not create-config. All config files are YAML.
