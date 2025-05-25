import sys
import time
import subprocess
import pytest
import asyncio
import requests
import socket
import os
import signal
from raillock.client import RailLockClient, RailLockConfig
from raillock.mcp_utils import get_tools_via_sse


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _is_coverage_enabled():
    """Check if coverage is actively collecting data during testing."""
    # Check for coverage command line indicators in argv
    if any("--cov" in arg for arg in sys.argv):
        return True

    # Check if coverage is actually running/collecting data
    try:
        import coverage

        # Check if coverage is currently measuring
        cov = coverage.Coverage()
        if cov._collectors:  # Coverage has active collectors
            return True
        # Alternative check - see if coverage is in the call stack
        import inspect

        for frame_info in inspect.stack():
            if "coverage" in frame_info.filename:
                return True
    except:
        pass

    # Check for pytest-cov being actively used
    try:
        # Check if pytest-cov plugin is loaded and has active coverage
        import pytest

        if hasattr(pytest, "config") and pytest.config:
            if hasattr(pytest.config, "pluginmanager"):
                if pytest.config.pluginmanager.hasplugin("pytest_cov"):
                    return True
    except:
        pass

    # Check for coverage environment variables indicating active collection
    if os.environ.get("COVERAGE_PROCESS_START") or os.environ.get("COV_CORE_SOURCE"):
        return True

    return False


# SSE integration test
@pytest.mark.anyio("asyncio")
async def test_sse_integration_with_real_server():
    port = get_free_port()
    server_script = os.path.abspath("examples/most-basic-sse/echo_server_sse.py")
    proc = subprocess.Popen(
        [sys.executable, server_script],
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PORT": str(port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Check if the server process exits immediately
    time.sleep(0.5)
    if proc.poll() is not None:
        err = proc.stderr.read().decode() if proc.stderr else None
        print(f"[DEBUG] Server process exited early. Stderr: {err}", flush=True)
        raise RuntimeError("SSE server process exited immediately after start")
    try:
        # Wait for server to start
        print(f"[DEBUG] Waiting for server to start on port {port}", flush=True)
        for i in range(30):
            try:
                url = f"http://localhost:{port}/sse"
                print(f"[DEBUG] Attempt {i + 1}: Polling {url}", flush=True)
                resp = requests.get(url, stream=True, timeout=0.5)
                if resp.status_code == 200:
                    print(f"[DEBUG] Server responded on attempt {i + 1}", flush=True)
                    resp.close()
                    break
                resp.close()
            except Exception as e:
                print(f"[DEBUG] Attempt {i + 1} failed: {e}", flush=True)
                time.sleep(0.5)
        else:
            # Print server stderr for debugging
            err = proc.stderr.read().decode() if proc.stderr else None
            print(f"[DEBUG] Server stderr: {err}", flush=True)
            raise RuntimeError("SSE server did not start in time")

        # Now run the real integration test
        tools, server_name = await get_tools_via_sse(f"http://localhost:{port}/sse")
        assert any(t.name == "echo" for t in tools)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# STDIO integration test


def test_stdio_integration(tmp_path):
    print("[DEBUG] Starting stdio integration test", flush=True)
    server_script = os.path.abspath("examples/most-basic/echo_server.py")
    print(f"[DEBUG] Using real echo_server.py at {server_script}", flush=True)

    client = None

    try:
        print("[DEBUG] Creating RailLockClient...", flush=True)
        client = RailLockClient(RailLockConfig())
        print("[DEBUG] RailLockClient created", flush=True)
        print("[DEBUG] About to call connect()", flush=True)

        # The RailLockClient will create and manage its own subprocess
        client.connect(f"stdio:{sys.executable} {server_script}")

        print("[DEBUG] client.connect() returned", flush=True)
        print(
            "[DEBUG] Connected. Available tools:", client._available_tools, flush=True
        )
        assert "echo" in client._available_tools
        print("[DEBUG] About to close client", flush=True)

    except Exception as e:
        print(f"[DEBUG] Exception occurred: {e}", flush=True)
        import traceback

        print(f"[DEBUG] Traceback: {traceback.format_exc()}", flush=True)
        raise
    finally:
        # Ensure proper cleanup
        if client:
            try:
                client.close()
                print("[DEBUG] Client closed.", flush=True)
            except Exception as e:
                print(f"[DEBUG] Error closing client: {e}", flush=True)


def test_minimal_debug():
    print("[DEBUG] Minimal test runs", flush=True)
    assert True


def test_tmp_path_only(tmp_path):
    print(f"[DEBUG] tmp_path is: {tmp_path}", flush=True)
    assert tmp_path.exists()
