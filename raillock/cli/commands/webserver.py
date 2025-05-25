import sys
import uvicorn

from raillock.client import RailLockClient
from raillock.config import RailLockConfig
from raillock.exceptions import RailLockError
from .web import create_app


def run_webserver(args):
    """Run the web server for tool review."""
    try:
        # Test server connectivity first
        print(f"Testing server connectivity: {args.server}")
        config = RailLockConfig()
        client = RailLockClient(config)
        client.test_server(args.server, timeout=getattr(args, "timeout", 30))
        print("✅ Server is reachable")

        # Create the web application
        app = create_app()

        # Set up global state
        app.state.server_url = args.server
        app.state.use_sse = getattr(args, "sse", False)

        # Start web server
        host = getattr(args, "host", "127.0.0.1")
        port = getattr(args, "port", 8080)

        print(f"\n🚀 Starting RailLock Web Review Server")
        print(f"📍 Server: {args.server}")
        print(f"🌐 Web Interface: http://{host}:{port}")
        print(f"📝 Configuration will be saved to: raillock_config.yaml")
        print(f"\nPress Ctrl+C to stop the server")

        uvicorn.run(app, host=host, port=port, log_level="info")

    except KeyboardInterrupt:
        print("\n[INFO] Web server stopped by user (Ctrl+C). Exiting.")
        sys.exit(130)
    except RailLockError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        if hasattr(app, "state") and hasattr(app.state, "client") and app.state.client:
            app.state.client.close()
