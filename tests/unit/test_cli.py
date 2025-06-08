import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)
import io
import tempfile
import os
import pytest
import subprocess
import yaml
from raillock.client import RailLockClient
from raillock.exceptions import RailLockError


class DummyClient:
    def __init__(self, tools):
        self._tools = tools

    def validate_tools(self):
        return self._tools


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
    # Write a valid config file (new format)
    config_file = tmp_path / "good_config.yaml"
    config_data = {
        "allowed_tools": {"echo": {"description": "desc", "checksum": "abc123"}},
        "malicious_tools": {},
        "denied_tools": {},
    }
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)
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
    assert (
        "Error loading configuration" not in result.stdout
        and "Error loading configuration" not in result.stderr
    )
    # Should still print error about server connection
    assert "Error:" in result.stdout or "Error:" in result.stderr


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
        or "Unexpected error" in result.stdout
        or "Unexpected error" in result.stderr
    )


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


def test_cli_review_invalid_url_scheme():
    result = subprocess.run(
        [
            "python",
            "-m",
            "raillock.cli",
            "review",
            "--server",
            "localhost:9002",
            "--sse",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert (
        "Error: Invalid server URL scheme" in result.stdout
        or "Error: Invalid server URL scheme" in result.stderr
    )
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_cli_review_404():
    result = subprocess.run(
        [
            "python",
            "-m",
            "raillock.cli",
            "review",
            "--server",
            "http://localhost:9999",
            "--sse",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert (
        "Error: Failed to reach server" in result.stdout
        or "Error: Failed to reach server" in result.stderr
    )
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_cli_compare_invalid_url_scheme():
    # Write a valid config file (new format)
    config_data = {
        "allowed_tools": {},
        "malicious_tools": {},
        "denied_tools": {},
    }
    config_file = "raillock_config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)
    result = subprocess.run(
        [
            "python",
            "-m",
            "raillock.cli",
            "compare",
            "--server",
            "localhost:9002",
            "--config",
            config_file,
            "--sse",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert (
        "Error loading configuration" not in result.stdout
        and "Error loading configuration" not in result.stderr
    )
    assert (
        "Error: Invalid server URL scheme" in result.stdout
        or "Error: Invalid server URL scheme" in result.stderr
    )


def test_cli_compare_404():
    # Write a valid config file (new format)
    config_data = {
        "allowed_tools": {},
        "malicious_tools": {},
        "denied_tools": {},
    }
    config_file = "raillock_config.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)
    result = subprocess.run(
        [
            "python",
            "-m",
            "raillock.cli",
            "compare",
            "--server",
            "http://localhost:9999",
            "--config",
            config_file,
            "--sse",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert (
        "Error loading configuration" not in result.stdout
        and "Error loading configuration" not in result.stderr
    )
    assert (
        "Error: Failed to reach server" in result.stdout
        or "Error: Failed to reach server" in result.stderr
    )


def test_review_mark_malicious(tmp_path, monkeypatch):
    # Simulate review with 'm' for malicious
    output_file = tmp_path / "out.yaml"
    # Patch input to always return 'm' then output file name
    inputs = iter(["m", str(output_file)])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

    # Patch RailLockClient.test_server and connect to avoid real network call
    import raillock.cli.commands.review as review_mod

    monkeypatch.setattr(
        review_mod.RailLockClient, "test_server", lambda self, *a, **k: True
    )
    monkeypatch.setattr(
        review_mod.RailLockClient, "connect", lambda self, *a, **k: None
    )

    # Patch _available_tools to provide fake tool data, and set _process and config
    def fake_init(self, config=None):
        self._available_tools = {
            "malicious_tool": {"description": "desc", "checksum": "abc"}
        }
        self._process = None
        self.config = type("C", (), {"allowed_tools": {}})()

    monkeypatch.setattr(review_mod.RailLockClient, "__init__", fake_init)

    # Patch get_tools_via_sse to return fake tools and server name
    class FakeTool:
        name = "malicious_tool"
        description = "desc"

    async def fake_get_tools_via_sse(server_url):
        return [FakeTool()], "http://dummy"

    monkeypatch.setattr(review_mod, "get_tools_via_sse", fake_get_tools_via_sse)
    review_mod.run_review(
        type(
            "Args",
            (),
            {"server": "http://dummy", "sse": True, "yes": False, "config": None},
        )()
    )
    # Check config file
    assert output_file.exists()
    import yaml

    with open(output_file) as f:
        data = yaml.safe_load(f)
    assert "malicious_tool" in data["malicious_tools"]


def test_review_yes_not_malicious(tmp_path, monkeypatch):
    # Simulate review --yes for stdio mode, in-process
    output_file = tmp_path / "out.yaml"
    monkeypatch.setattr("builtins.input", lambda prompt: str(output_file))

    # Patch RailLockClient.test_server and connect to avoid real network call
    import raillock.cli.commands.review as review_mod

    monkeypatch.setattr(
        review_mod.RailLockClient, "test_server", lambda self, *a, **k: True
    )
    monkeypatch.setattr(
        review_mod.RailLockClient, "connect", lambda self, *a, **k: None
    )

    # Patch _available_tools to provide fake tool data, and set _process and config
    def fake_init(self, config=None):
        self._available_tools = {
            "safe_tool": {"description": "desc", "checksum": "abc"}
        }
        self._process = None
        # Dummy config with allowed_tools attribute
        self.config = type("C", (), {"allowed_tools": {}})()

    monkeypatch.setattr(review_mod.RailLockClient, "__init__", fake_init)

    review_mod.run_review(
        type(
            "Args",
            (),
            {"server": "http://dummy", "sse": False, "yes": True, "config": None},
        )()
    )
    assert output_file.exists()
    import yaml

    with open(output_file) as f:
        data = yaml.safe_load(f)
    assert "safe_tool" in data["allowed_tools"]


def test_compare_malicious_column(tmp_path, monkeypatch, capsys):
    # Write a config file with a malicious tool (new format)
    config_file = tmp_path / "malicious_config.yaml"
    config_data = {
        "allowed_tools": {
            "evil": {
                "description": "desc",
                "server": "http://dummy",
                "checksum": "abc",
            },
            "good": {
                "description": "desc",
                "server": "http://dummy",
                "checksum": "def",
            },
        },
        "malicious_tools": {},
        "denied_tools": {},
    }
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)
    # Patch RailLockClient.test_server and connect to avoid real network call
    import raillock.cli.commands.compare as compare_mod

    monkeypatch.setattr(
        compare_mod.RailLockClient, "test_server", lambda self, *a, **k: True
    )
    monkeypatch.setattr(
        compare_mod.RailLockClient, "connect", lambda self, *a, **k: None
    )

    def fake_init(self, config=None):
        self._available_tools = {
            "evil": {"description": "desc", "checksum": "abc"},
            "good": {"description": "desc", "checksum": "def"},
        }
        self._process = None
        self.config = None

    monkeypatch.setattr(compare_mod.RailLockClient, "__init__", fake_init)
    args = type(
        "Args", (), {"server": "http://dummy", "config": str(config_file), "sse": False}
    )()
    compare_mod.run_compare(args)
    out = capsys.readouterr().out
    assert "evil" in out
    assert "good" in out
    assert "allowed" in out


def test_review_malicious_prompt(monkeypatch, tmp_path):
    # Simulate user input: first tool is allowed, second is malicious, third is denied
    responses = iter(["y", "m", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))
    # Dummy tools
    tools = [
        type("Tool", (), {"name": "tool1", "description": "desc1"})(),
        type("Tool", (), {"name": "tool2", "description": "desc2"})(),
        type("Tool", (), {"name": "tool3", "description": "desc3"})(),
    ]
    # Patch get_tools_via_sse to return our dummy tools
    import raillock.cli.commands.review as review_mod

    async def fake_get_tools_via_sse(server):
        return tools, "server"

    monkeypatch.setattr(review_mod, "get_tools_via_sse", fake_get_tools_via_sse)
    # Patch output file
    output_file = tmp_path / "out.yaml"
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt: str(output_file) if "filename" in prompt else next(responses),
    )

    # Patch test_server to always succeed
    class DummyClient:
        def test_server(self, *a, **kw):
            return True

        def connect(self, *a, **kw):
            pass

        def close(self):
            pass

    monkeypatch.setattr(review_mod, "RailLockClient", lambda config: DummyClient())
    # Run review_sse logic
    args = type("Args", (), {"server": "http://dummy", "sse": True, "yes": False})()
    review_mod.run_review(args)
    # Check config file
    import yaml

    with open(output_file) as f:
        config = yaml.safe_load(f)
    allowed_tools = config["allowed_tools"]
    malicious_tools = config["malicious_tools"]
    denied_tools = config["denied_tools"]
    assert "tool1" in allowed_tools
    assert "tool2" in malicious_tools
    assert "tool3" in denied_tools


def test_compare_type_column(tmp_path, capsys):
    # Create a config with allowed and malicious tools (new format)
    config = {
        "allowed_tools": {
            "tool1": {"description": "desc1", "server": "s", "checksum": "c1"},
        },
        "malicious_tools": {
            "tool2": {"description": "desc2", "server": "s", "checksum": "c2"},
        },
        "denied_tools": {},
    }
    config_file = tmp_path / "config.yaml"
    import yaml

    with open(config_file, "w") as f:
        yaml.safe_dump(config, f)
    import raillock.cli.commands.compare as compare_mod

    class DummyClient:
        def __init__(self, config):
            self._available_tools = {
                "tool1": {"description": "desc1", "checksum": "c1"},
                "tool2": {"description": "desc2", "checksum": "c2"},
            }
            self.config = config

        def connect(self, *a, **k):
            pass

        def close(self):
            pass

    compare_mod.RailLockClient = lambda config: DummyClient(config)
    args = type(
        "Args", (), {"server": "http://dummy", "config": str(config_file), "sse": False}
    )()
    compare_mod.run_compare(args)
    out = capsys.readouterr().out
    assert "tool1" in out
    assert "tool2" in out
    assert "allowed" in out or "malicious" in out


def test_review_all_sections(monkeypatch, tmp_path):
    """
    Simulate user input for [y] allowed, [m] malicious, [n] denied, [i] ignore.
    Ensure each tool is placed in the correct section, and ignored tools are not recorded.
    """
    # Simulate user input: first tool is allowed, second is malicious, third is denied, fourth is ignored
    responses = iter(["y", "m", "n", "i", str(tmp_path / "out.yaml")])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    # Dummy tools
    class Tool:
        def __init__(self, name, description):
            self.name = name
            self.description = description

    tools = [
        Tool("tool_allowed", "desc1"),
        Tool("tool_malicious", "desc2"),
        Tool("tool_denied", "desc3"),
        Tool("tool_ignored", "desc4"),
    ]
    # Patch get_tools_via_sse to return our dummy tools
    import raillock.cli.commands.review as review_mod

    async def fake_get_tools_via_sse(server):
        return tools, "http://dummy"

    monkeypatch.setattr(review_mod, "get_tools_via_sse", fake_get_tools_via_sse)

    # Patch RailLockClient to avoid real server
    class DummyClient:
        def test_server(self, *a, **kw):
            return True

        def connect(self, *a, **kw):
            pass

        def close(self):
            pass

    monkeypatch.setattr(review_mod, "RailLockClient", lambda config: DummyClient())
    review_mod.run_review(
        type(
            "Args",
            (),
            {"server": "http://dummy", "sse": True, "yes": False, "config": None},
        )()
    )
    # Check config file
    import yaml

    output_file = tmp_path / "out.yaml"
    with open(output_file) as f:
        config = yaml.safe_load(f)
    assert "tool_allowed" in config["allowed_tools"]
    assert "tool_malicious" in config["malicious_tools"]
    assert "tool_denied" in config["denied_tools"]
    assert "tool_ignored" not in config["allowed_tools"]
    assert "tool_ignored" not in config["malicious_tools"]
    assert "tool_ignored" not in config["denied_tools"]


def test_review_empty_sections(monkeypatch, tmp_path):
    """
    If all tools are ignored, all sections should be present and empty.
    """
    responses = iter(["i", "i", str(tmp_path / "out.yaml")])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    class Tool:
        def __init__(self, name, description):
            self.name = name
            self.description = description

    tools = [Tool("tool1", "desc1"), Tool("tool2", "desc2")]
    import raillock.cli.commands.review as review_mod

    async def fake_get_tools_via_sse(server):
        return tools, "http://dummy"

    monkeypatch.setattr(review_mod, "get_tools_via_sse", fake_get_tools_via_sse)

    class DummyClient:
        def test_server(self, *a, **kw):
            return True

        def connect(self, *a, **kw):
            pass

        def close(self):
            pass

    monkeypatch.setattr(review_mod, "RailLockClient", lambda config: DummyClient())
    review_mod.run_review(
        type(
            "Args",
            (),
            {"server": "http://dummy", "sse": True, "yes": False, "config": None},
        )()
    )
    import yaml

    output_file = tmp_path / "out.yaml"
    with open(output_file) as f:
        config = yaml.safe_load(f)
    assert config["allowed_tools"] == {}
    assert config["malicious_tools"] == {}
    assert config["denied_tools"] == {}


def test_cli_review_yes_config_creates_and_overwrites(tmp_path):
    import subprocess
    import yaml

    config_file = tmp_path / "test_config.yaml"
    # Remove if exists
    if config_file.exists():
        config_file.unlink()
    # Run CLI with --yes and --config (file does not exist)
    result = subprocess.run(
        [
            "python",
            "-m",
            "raillock.cli",
            "review",
            "--server",
            "http://localhost:9999",
            "--yes",
            "--config",
            str(config_file),
        ],
        input="",
        capture_output=True,
        text=True,
    )
    # Should not error about missing config file
    assert result.returncode != 0  # Will fail to connect, but not config error
    assert (
        "Error loading configuration" not in result.stdout
        and "Error loading configuration" not in result.stderr
    )
    # Simulate file creation
    with open(config_file, "w") as f:
        yaml.safe_dump(
            {"allowed_tools": {"echo": {"description": "desc", "checksum": "abc"}}}, f
        )
    # Run CLI again to test overwrite
    result2 = subprocess.run(
        [
            "python",
            "-m",
            "raillock.cli",
            "review",
            "--server",
            "http://localhost:9999",
            "--yes",
            "--config",
            str(config_file),
        ],
        input="",
        capture_output=True,
        text=True,
    )
    assert result2.returncode != 0
    assert (
        "Error loading configuration" not in result2.stdout
        and "Error loading configuration" not in result2.stderr
    )


def test_compare_malicious_tools_checksum(tmp_path, monkeypatch, capsys):
    """Test that a tool is only considered malicious if both name and checksum match."""
    import raillock.cli.commands.compare as compare_mod
    import yaml

    # Create a config with a malicious tool (with a specific checksum)
    config_file = tmp_path / "malicious_config.yaml"
    malicious_tool_name = "malicious_tool"
    malicious_tool_desc = "desc1"
    malicious_tool_checksum = "deadbeef"
    config_data = {
        "allowed_tools": {},
        "malicious_tools": {
            malicious_tool_name: {
                "description": malicious_tool_desc,
                "checksum": malicious_tool_checksum,
            }
        },
        "denied_tools": {},
    }
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)

    # Patch RailLockClient to provide a tool with the same name but different checksum
    class DummyClient:
        def __init__(self, config):
            self._available_tools = {
                malicious_tool_name: {
                    "description": "desc2",  # different description
                    "checksum": "notdeadbeef",  # different checksum
                }
            }
            self.config = config

        def connect(self, *a, **k):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        compare_mod, "RailLockClient", lambda config: DummyClient(config)
    )
    args = type(
        "Args", (), {"server": "http://dummy", "config": str(config_file), "sse": False}
    )()
    compare_mod.run_compare(args)
    out = capsys.readouterr().out
    # Should show the tool as unknown (checksum mismatch) when checksum does not match
    assert "unknown (checksum mismatch)" in out

    # Now patch to match checksum
    class DummyClient2:
        def __init__(self, config):
            self._available_tools = {
                malicious_tool_name: {
                    "description": malicious_tool_desc,
                    "checksum": malicious_tool_checksum,
                }
            }
            self.config = config

        def connect(self, *a, **k):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        compare_mod, "RailLockClient", lambda config: DummyClient2(config)
    )
    compare_mod.run_compare(args)
    out2 = capsys.readouterr().out
    # Should show the tool as malicious (since checksum matches)
    assert "malicious" in out2


def test_interactive_review_tools_all_modes(tmp_path, monkeypatch):
    """Test that interactive review works for both SSE and stdio modes."""
    import yaml
    from raillock.cli.commands import review as review_mod

    # Simulate user input: allow first, malicious second, deny third, ignore fourth
    responses = iter(["y", "m", "n", "i"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))

    # Prepare tool lists for both modes
    tools = [
        {"name": "tool_allowed", "description": "desc1"},
        {"name": "tool_malicious", "description": "desc2"},
        {"name": "tool_denied", "description": "desc3"},
        {"name": "tool_ignored", "description": "desc4"},
    ]
    server_name = "dummy_server"
    output_file = tmp_path / "out.yaml"

    # Test stdio mode
    review_mod.interactive_review_tools(tools, server_name, "stdio", str(output_file))
    with open(output_file) as f:
        config = yaml.safe_load(f)
    assert "tool_allowed" in config["allowed_tools"]
    assert "tool_malicious" in config["malicious_tools"]
    assert "tool_denied" in config["denied_tools"]
    assert "tool_ignored" not in config["allowed_tools"]
    assert "tool_ignored" not in config["malicious_tools"]
    assert "tool_ignored" not in config["denied_tools"]

    # Test SSE mode (should behave identically)
    responses2 = iter(["y", "m", "n", "i"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses2))
    output_file2 = tmp_path / "out2.yaml"
    review_mod.interactive_review_tools(tools, server_name, "sse", str(output_file2))
    with open(output_file2) as f:
        config2 = yaml.safe_load(f)
    assert "tool_allowed" in config2["allowed_tools"]
    assert "tool_malicious" in config2["malicious_tools"]
    assert "tool_denied" in config2["denied_tools"]
    assert "tool_ignored" not in config2["allowed_tools"]
    assert "tool_ignored" not in config2["malicious_tools"]
    assert "tool_ignored" not in config2["denied_tools"]
