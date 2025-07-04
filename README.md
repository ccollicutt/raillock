![RailLock Logo](img/raillock.png)

# raillock

Raillock is an MCP security CLI and Python library that can be used to validate MCP servers and the tools they expose. It's most basic function is to calculate the checksum of the tools the MCP server exposes, including their descriptions, and compare it with the checksum of the tools in the client's config file.

1. A CLI tool that can be used to validate MCP servers.
2. A Python library for MCP clients that can be used to validate MCP servers.

The CLI tool could be used outside a Python environment to validate MCP servers, but of course the client library would need to be used inside the Python environment, specifically in the MCP client of an AI agent.

## Why is this important?

Using AI tools is different from using traditional software in that they are "programmable" through natural language. For example, currently MCP servers provide a description, or the function's doc string, of the tool, which can contain malicious instructions to the agent using the tool.

## Caveats and the Feedback Stage

- This is a work in progress and the API is not yet stable.
- It has not yet been tested in a production environment.
- It has not yet been tested against production-grade MCP servers.

We are looking for feedback from users!

## Features

- Connect to MCP servers (HTTP/SSE and stdio)
- Validate available tools with checksum verification
- Manage tool access permissions via CLI or web interface
- Configuration-based tool validation with YAML configs
- **Web UI** for visual tool management and configuration
- Example server and client implementations

## Installation

With UV:

```bash
git clone https://github.com/ccollicutt/raillock.git
cd raillock
pipx install uv
uv venv .venv --python 3.11
source .venv/bin/activate
uv sync
uv pip install -e ".[dev]"
```

The raillock CLI should now be available.

## Usage

### Using the CLI

#### Review tools on a server

```sh
# Review tools from an HTTP server
raillock review --server http://localhost:8000

# Review tools from an SSE server
raillock review --server http://localhost:8000/sse --sse

# Review tools from a stdio server (e.g., a Python script)
raillock review --server "stdio:python examples/most-basic/echo_server.py"
```

#### Auto-accept all tools and generate a config file

```sh
raillock review --server http://localhost:8000 --yes
```

#### Compare a config file to a running server

```sh
raillock compare --server http://localhost:8000 --config raillock_config.yaml
```

#### Web Interface

![RailLock Web Interface](img/web-gui.png)

RailLock includes a web interface for easier tool management and configuration:

```sh
# Start web server for an SSE MCP server
raillock webserver --server http://localhost:8000/sse --sse --host 0.0.0.0 --port 8080

# Start web server for a stdio MCP server
raillock webserver --server "stdio:python examples/most-basic/echo_server.py" --host 0.0.0.0 --port 8080
```

The web interface provides:

- **Tool Discovery**: Browse all available tools from the MCP server
- **Interactive Review**: Allow/deny tools with a visual interface
- **Configuration Management**: Generate and download YAML config files
- **Real-time Comparison**: Compare existing configs against live servers

Access the web interface at `http://localhost:8080` after starting the webserver.

---

### Using the Library

```python
import asyncio
from raillock import RailLockClient, RailLockConfig

# Allow the 'echo' tool (accept any checksum for demo; in production, use the real checksum)
ALLOWED_TOOLS = {"echo": "*"}
rail_config = RailLockConfig(allowed_tools=ALLOWED_TOOLS)
rail_client = RailLockClient(rail_config)

# Example async usage with a stdio MCP server
async def main():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from pathlib import Path

    server_script = Path("examples/most-basic/echo_server.py").resolve()
    server_params = StdioServerParameters(command="python", args=[str(server_script)])

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            # Filter tools using RailLock
            allowed_tools = rail_client.filter_tools(await session.list_tools().tools)
            print("Allowed tools:", [tool.name for tool in allowed_tools])
            # Call the 'echo' tool if allowed
            if any(tool.name == "echo" for tool in allowed_tools):
                result = await session.call_tool("echo", {"text": "Hello, MCP with RailLock!"})
                print("Echo result:", getattr(result, "content", result))

if __name__ == "__main__":
    asyncio.run(main())
```

## Further Reading on MCP Security

- [Invariant Labs - Tool Poisoning](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)
- [Trail of Bits - Jumping the Line](https://blog.trailofbits.com/2025/04/21/jumping-the-line-how-mcp-servers-can-attack-you-before-you-ever-use-them/)
- [Trail of Bits - Conversation History](https://blog.trailofbits.com/2025/04/23/how-mcp-servers-can-steal-your-conversation-history/)
