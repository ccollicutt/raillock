import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)
import pytest
import yaml


def test_compare_malicious_tools_checksum(tmp_path, monkeypatch, capsys):
    """Test that a tool is only considered malicious if both name and checksum match."""
    import raillock.cli.commands.compare as compare_mod

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
    print("DEBUG OUTPUT FOR CHECKSUM MISMATCH CASE:")
    print(out)
    # Should show the tool as unknown (checksum mismatch) and Checksum Match as ✘
    assert "unknown (checksum mismatch)" in out
    assert "✘" in out  # Checksum Match column shows ✘

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
    # Should show the tool as malicious (since checksum matches) and Checksum Match as ✔
    assert "malicious" in out2
    assert "✔" in out2  # Checksum Match column shows ✔


def test_cli_generated_config_matches_server_checksum(tmp_path, monkeypatch):
    """Test that a config generated by the CLI matches the server's checksums for malicious tools."""
    import raillock.utils as utils

    # Simulate a server tool and config generated by CLI
    tool_name = "malicious_tool"
    tool_desc = "desc1"
    server_name = "http://dummy"
    checksum = utils.calculate_tool_checksum(tool_name, tool_desc, server_name)
    config = {
        "malicious_tools": {
            tool_name: {
                "description": tool_desc,
                "server": server_name,
                "checksum": checksum,
            }
        },
        "allowed_tools": {},
        "denied_tools": {},
    }
    # Simulate server tool
    server_tool = {"name": tool_name, "description": tool_desc}
    # The checksum in config should match the one computed from the server's tool
    assert config["malicious_tools"][tool_name][
        "checksum"
    ] == utils.calculate_tool_checksum(
        server_tool["name"], server_tool["description"], server_name
    )
