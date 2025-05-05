# most-basic

This is a minimal example of an Echo MCP client/server.

All dependencies are pinned in `pyproject.toml`.

## MCP 1.5.0

For whatever reason, MCP 1.6.0 doesn't work with the most basic usage of the client.

**⚠️ IMPORTANT: MCP 1.6.0 is NOT compatible with this project. Use MCP 1.5.0. ⚠️**

> **Note:** If you install or upgrade to `mcp==1.6.0`, the client and server will hang or fail to communicate. This project is tested and works with `mcp==1.5.0` only.

## Setup

1. Create and activate a Python virtual environment:
   ```sh
   uv venv
   source .venv/bin/activate
   ```
2. Install dependencies (reproducibly):

   ```sh
   uv sync
   ```

   This will use the `uv.lock` and `pyproject.toml` for a reproducible install.

   Or, to install directly (not recommended for production):

   ```sh
   uv pip install mcp==1.5.0
   ```

## Usage

### Run the Echo Client (which launches the server as a subprocess)

```sh
python echo_client.py
```

- The client will list available tools and call the `echo` tool.
- All logs are written to both the console and `echo_client.log`.
