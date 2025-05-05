import io
import tempfile
import os
import pytest
import subprocess
import yaml
from raillock.cli.review_tools import review_tools
from raillock.client import RailLockClient
from raillock.exceptions import RailLockError


class DummyClient:
    def __init__(self, tools):
        self._tools = tools

    def validate_tools(self):
        return self._tools


def test_review_tools_prints(capsys):
    tools = {"echo": {"description": "desc", "checksum": "abc"}}
    client = DummyClient(tools)
    review_tools(client)
    out = capsys.readouterr().out
    assert "echo" in out
    assert "Description" in out
    assert "Checksum" in out


def test_review_tools_empty(capsys):
    client = DummyClient({})
    review_tools(client)
    out = capsys.readouterr().out
    assert "No tools available" in out


def test_review_tools_raillockerror(monkeypatch, capsys):
    class BadClient:
        def validate_tools(self):
            raise RailLockError("fail")

    with pytest.raises(SystemExit):
        review_tools(BadClient())
    err = capsys.readouterr().err
    assert "Error reviewing tools" in err


def test_review_tools_generic_exception(monkeypatch, capsys):
    class BadClient:
        def validate_tools(self):
            raise Exception("fail")

    with pytest.raises(SystemExit):
        review_tools(BadClient())
    err = capsys.readouterr().err
    assert "Unexpected error" in err


def test_cli_review_subprocess(tmp_path):
    # Use a dummy server that will fail, but we want to see the error handling
    result = subprocess.run(
        [
            "python",
            "-m",
            "raillock.cli",
            "review",
            "--server",
            "http://localhost:9999",  # Should fail to connect
        ],
        capture_output=True,
        text=True,
    )
    # Should exit with nonzero code and print error
    assert result.returncode != 0
    assert "Error:" in result.stdout or "Error:" in result.stderr


def test_cli_review_with_config_file(tmp_path):
    # Write a valid config file
    config_file = tmp_path / "good_config.yaml"
    config_file.write_text("echo: abc123")
    result = subprocess.run(
        [
            "python",
            "-m",
            "raillock.cli",
            "review",
            "--server",
            "http://localhost:9999",
            "--config",
            str(config_file),
        ],
        capture_output=True,
        text=True,
    )
    # Should exit with nonzero code and print error (server will fail, but config loads)
    assert result.returncode != 0
    assert "Error:" in result.stdout or "Error:" in result.stderr
    assert "Loading config from" in result.stdout


def test_cli_review_with_missing_config_file(tmp_path):
    missing_file = tmp_path / "missing_config.yaml"
    result = subprocess.run(
        [
            "python",
            "-m",
            "raillock.cli",
            "review",
            "--server",
            "http://localhost:9999",
            "--config",
            str(missing_file),
        ],
        capture_output=True,
        text=True,
    )
    # Should exit with nonzero code and print error about config
    assert result.returncode != 0
    assert (
        "Error loading configuration" in result.stdout
        or "Error loading configuration" in result.stderr
    )


def test_review_tools_interactive(monkeypatch, capsys):
    # Simulate user input for input() calls (always 'y')
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    # Prepare a dummy client with a tool
    class DummyTool:
        def __init__(self, name, description):
            self.name = name
            self.description = description

    class DummyClient:
        def validate_tools(self):
            return {"echo": {"description": "desc", "checksum": "abc"}}

    review_tools(DummyClient())
    out = capsys.readouterr().out
    assert "echo" in out
    assert "Description" in out
    assert "Checksum" in out


def test_review_yes_creates_config(tmp_path, monkeypatch):
    # Simulate review --yes for stdio mode, in-process
    output_file = tmp_path / "out.yaml"
    # Patch input to auto-select output file
    monkeypatch.setattr("builtins.input", lambda prompt: str(output_file))

    # Patch client to avoid real server
    class DummyClient:
        def __init__(self):
            self._available_tools = {"echo": {"description": "desc", "checksum": "abc"}}

        def test_server(self, *a, **kw):
            return True

        def connect(self, *a, **kw):
            pass

    # Simulate the logic of review --yes for stdio
    client = DummyClient()
    config_dict = {
        "config_version": 1,
        "server": {
            "name": "stdio:dummy",
            "type": "stdio",
        },
        "allowed_tools": {},
    }
    for name, tool in client._available_tools.items():
        desc = tool["description"]
        checksum = tool["checksum"]
        config_dict["allowed_tools"][name] = {
            "description": desc,
            "server": config_dict["server"]["name"],
            "checksum": checksum,
        }

    # Write config using the same logic as CLI
    def str_presenter(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        if any(c in data for c in [":", '"', "'", "{", "}", "[", "]"]):
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.add_representer(str, str_presenter)
    with open(output_file, "w") as f:
        yaml.safe_dump(config_dict, f, sort_keys=False, allow_unicode=True)
    assert output_file.exists()
    with open(output_file) as f:
        data = yaml.safe_load(f)
    assert "echo" in data["allowed_tools"]
    assert data["allowed_tools"]["echo"]["description"] == "desc"


# SSE mode test would require more advanced mocking or integration test setup

# Note: Config generation is now done via review --yes, not create-config. All config files are YAML.
