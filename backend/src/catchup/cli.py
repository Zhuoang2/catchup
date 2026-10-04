"""Command line entry point for the self-hosted server."""

import argparse

import uvicorn

from catchup.main import create_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="catchup")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Start the CatchUp web server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.command == "serve":
        uvicorn.run(create_app(), host=args.host, port=args.port)
