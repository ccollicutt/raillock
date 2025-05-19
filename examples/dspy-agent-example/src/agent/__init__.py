import os

RAILLOCK_CLIENT = None

if os.environ.get("RAILLOCK_ENABLE", "false").lower() == "true":
    from pathlib import Path
    import raillock
    from raillock import RailLockClient, RailLockConfig
    from raillock.mcp_utils import monkeypatch_raillock_tools
    from raillock.utils import debug_print

    # Print the import path for RailLock (critical for debugging)
    print("[DEBUG][RailLock] imported from:", raillock.__file__)

    # Optionally, print sys.path for further debugging
    if hasattr(raillock, "is_debug") and raillock.is_debug():
        import sys

        debug_print("sys.path:", sys.path)

    # Allow config path override via env, fallback to local file
    config_path = Path(
        os.environ.get(
            "RAILLOCK_CONFIG", Path(__file__).parent / "raillock_config.yaml"
        )
    )
    print("[RailLock] Loading config from:", config_path)
    rail_config = RailLockConfig.from_file(str(config_path))
    print("[RailLock] Allowed tools in config:", list(rail_config.allowed_tools.keys()))
    RAILLOCK_CLIENT = RailLockClient(rail_config)
    # monkeypatch_raillock_tools will be called in agent.py after session is created
