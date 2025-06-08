import textwrap
import yaml
from starlette.responses import JSONResponse

from raillock.client import RailLockClient
from raillock.config import RailLockConfig
from raillock.mcp_utils import get_tools_via_sse
from raillock.utils import calculate_tool_checksum
from raillock.config_utils import (
    build_config_dict,
    save_config_to_file,
    config_dict_to_yaml_string,
    compare_config_with_server,
)


async def get_tools_api(request):
    """API endpoint to get tools from the server."""
    state = request.app.state

    try:
        if state.use_sse:
            # Use MCP protocol for SSE
            tools, real_server_name = await get_tools_via_sse(state.server_url)
            state.server_name = real_server_name or state.server_url
            state.server_type = "sse"

            # Convert tools to dict format
            tools_list = []
            for tool in tools:
                name = getattr(tool, "name", None)
                desc = getattr(tool, "description", "")
                tools_list.append({"name": name, "description": desc})
            state.tools = tools_list
        else:
            # Use stdio or HTTP
            if state.client is None:
                config = RailLockConfig()
                state.client = RailLockClient(config)
                await state.client.connect_async(state.server_url)

            state.server_name = state.server_url
            state.server_type = (
                "stdio" if state.server_url.startswith("stdio:") else "http"
            )

            tools_list = []
            for name, tool in state.client._available_tools.items():
                tools_list.append({"name": name, "description": tool["description"]})
            state.tools = tools_list

        return JSONResponse(
            {
                "tools": state.tools,
                "server_name": state.server_name,
                "server_type": state.server_type,
            }
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def preview_config_api(request):
    """API endpoint to preview the configuration without saving."""
    state = request.app.state

    try:
        data = await request.json()
        choices = data.get("choices", {})

        config_dict = build_config_dict(
            state.tools, choices, state.server_name, state.server_type
        )

        # Generate summary stats
        total_tools = len(state.tools)
        allowed_count = len(config_dict["allowed_tools"])
        denied_count = len(config_dict["denied_tools"])
        malicious_count = len(config_dict["malicious_tools"])
        ignored_count = total_tools - (allowed_count + denied_count + malicious_count)

        summary = {
            "allowed": allowed_count,
            "denied": denied_count,
            "malicious": malicious_count,
            "ignored": ignored_count,
        }

        # Generate YAML content using shared utility
        yaml_content = config_dict_to_yaml_string(config_dict)

        return JSONResponse(
            {"success": True, "summary": summary, "yaml_content": yaml_content}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def save_config_api(request):
    """API endpoint to save the configuration based on user choices."""
    state = request.app.state

    try:
        data = await request.json()
        choices = data.get("choices", {})
        filename = data.get("filename", "raillock_config.yaml")

        config_dict = build_config_dict(
            state.tools, choices, state.server_name, state.server_type
        )

        # Save config using shared utility
        save_config_to_file(config_dict, filename)

        return JSONResponse({"success": True, "config_path": filename})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def compare_config_api(request):
    """API endpoint to compare a configuration file against the server."""
    state = request.app.state

    try:
        data = await request.json()
        config_content = data.get("config_content", "")

        # Parse the uploaded YAML config
        try:
            config_data = yaml.safe_load(config_content)
        except yaml.YAMLError as e:
            return JSONResponse({"error": f"Invalid YAML file: {e}"}, status_code=400)

        # Get server tools
        if state.use_sse:
            # Use MCP protocol for SSE
            tools, _ = await get_tools_via_sse(state.server_url)
            server_tools = {
                t.name: {
                    "description": t.description,
                    "checksum": calculate_tool_checksum(
                        t.name, t.description, state.server_name
                    ),
                }
                for t in tools
            }
        else:
            # Use stdio or HTTP
            if state.client is None:
                config = RailLockConfig()
                state.client = RailLockClient(config)
                await state.client.connect_async(state.server_url)
            server_tools = state.client._available_tools

        # Use shared comparison function
        comparison_data, summary = compare_config_with_server(config_data, server_tools)

        return JSONResponse(
            {"success": True, "summary": summary, "comparison_data": comparison_data}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def save_manual_config_api(request):
    """API endpoint to save manually edited YAML configuration."""
    try:
        data = await request.json()
        yaml_content = data.get("yaml_content", "")
        filename = data.get("filename", "raillock_config.yaml")

        if not yaml_content.strip():
            return JSONResponse(
                {"error": "YAML content cannot be empty"}, status_code=400
            )

        # Ensure filename has .yaml extension
        if not filename.endswith((".yaml", ".yml")):
            filename += ".yaml"

        # Validate YAML by trying to parse it
        try:
            yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return JSONResponse({"error": f"Invalid YAML: {e}"}, status_code=400)

        # Save the YAML content directly
        with open(filename, "w") as f:
            f.write(yaml_content)

        return JSONResponse({"success": True, "config_path": filename})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
