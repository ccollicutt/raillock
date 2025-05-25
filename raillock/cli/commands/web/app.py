import os
from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from .api import (
    get_tools_api,
    preview_config_api,
    save_config_api,
    compare_config_api,
    save_manual_config_api,
)


# Get the directory where this file is located
BASE_DIR = Path(__file__).parent


# Global state for the web server
class WebServerState:
    def __init__(self):
        self.tools = []
        self.server_name = None
        self.server_type = None
        self.client = None
        self.server_url = None
        self.use_sse = False


async def home(request):
    """Serve the main review interface."""
    template_path = BASE_DIR / "templates" / "index.html"
    with open(template_path, "r") as f:
        content = f.read()
    return HTMLResponse(content)


def create_app():
    """Create and configure the Starlette application."""

    # Routes
    routes = [
        Route("/", home),
        Route("/api/tools", get_tools_api),
        Route("/api/preview-config", preview_config_api, methods=["POST"]),
        Route("/api/save-config", save_config_api, methods=["POST"]),
        Route("/api/compare-config", compare_config_api, methods=["POST"]),
        Route("/api/save-manual-config", save_manual_config_api, methods=["POST"]),
        Mount(
            "/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static"
        ),
    ]

    # Middleware
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    # Create application
    app = Starlette(routes=routes, middleware=middleware)

    # Initialize state
    app.state = WebServerState()

    return app
