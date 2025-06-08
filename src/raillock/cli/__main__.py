import argparse
import sys
import traceback
from raillock.cli.commands.review import run_review
from raillock.cli.commands.compare import run_compare
from raillock.cli.commands.webserver import run_webserver


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="""RailLock CLI\n\nExamples:\n  raillock review --server http://localhost:8000\n  raillock review --server http://localhost:8000/sse --sse\n  raillock review --server stdio:my_server_executable\n  raillock review --server http://localhost:8000/sse --sse --yes\n  raillock review --server stdio:my_server_executable --yes\n  raillock compare --server http://localhost:8000/sse --config raillock_config.yaml\n  raillock webserver --server http://localhost:8000/sse --sse --host 0.0.0.0 --port 8080\n\nUse --yes to auto-accept all tools and generate a config file (works for SSE and stdio).\nUse webserver to start a web interface for reviewing tools.\nFor more, see the docs/cli.md\n""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Review command
    review_parser = subparsers.add_parser(
        "review", help="Review available tools and optionally generate a config file"
    )
    review_parser.add_argument(
        "--server",
        required=True,
        help="Server URL (e.g. http://localhost:8000, --sse for SSE) or stdio command (e.g. stdio:my_server_executable)",
    )
    review_parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    review_parser.add_argument("--config", help="Configuration file path")
    review_parser.add_argument(
        "--timeout", type=int, default=30, help="Connection timeout in seconds"
    )
    review_parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-accept all tools and write a config file (non-interactive)",
    )

    # Compare command
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare a config file to a server and output allowed/disallowed tools as a table",
    )
    compare_parser.add_argument(
        "--server",
        required=True,
        help="Server URL (e.g. http://localhost:8000, --sse for SSE) or stdio command (e.g. stdio:my_server_executable)",
    )
    compare_parser.add_argument(
        "--config", required=True, help="Configuration file path"
    )
    compare_parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    compare_parser.add_argument(
        "--timeout", type=int, default=30, help="Connection timeout in seconds"
    )

    # Web server command
    webserver_parser = subparsers.add_parser(
        "webserver",
        help="Start a web server for reviewing tools via a web interface",
    )
    webserver_parser.add_argument(
        "--server",
        required=True,
        help="Server URL (e.g. http://localhost:8000, --sse for SSE) or stdio command (e.g. stdio:my_server_executable)",
    )
    webserver_parser.add_argument(
        "--sse", action="store_true", help="Use SSE transport"
    )
    webserver_parser.add_argument(
        "--timeout", type=int, default=30, help="Connection timeout in seconds"
    )
    webserver_parser.add_argument(
        "--host", default="127.0.0.1", help="Web server host (default: 127.0.0.1)"
    )
    webserver_parser.add_argument(
        "--port", type=int, default=8080, help="Web server port (default: 8080)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "review":
        run_review(args)
    elif args.command == "compare":
        run_compare(args)
    elif args.command == "webserver":
        run_webserver(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
