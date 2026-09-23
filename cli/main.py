"""Sovereign Matrix command-line entry point."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matrix",
        description="Operate and validate the Sovereign Matrix.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Check required files and Python dependencies.")
    subparsers.add_parser("dashboard-build", help="Build the dashboard with npm.")

    run_parser = subparsers.add_parser("run", help="Start the Matrix engine.")
    run_parser.add_argument(
        "--bus-url",
        help="Neural bus endpoint (overrides ZMQ_BUS_URL for this process).",
    )
    return parser


def check_environment() -> int:
    required_files = ("matrix_main.py", "dashboard/package.json", "dashboard/package-lock.json")
    missing = [path for path in required_files if not (ROOT / path).is_file()]
    if missing:
        for path in missing:
            print(f"missing: {path}", file=sys.stderr)
        return 1

    dependencies = ("zmq", "pydantic")
    missing_dependencies = [
        dependency
        for dependency in dependencies
        if importlib.util.find_spec(dependency) is None
    ]
    if missing_dependencies:
        print(
            "missing Python dependencies: " + ", ".join(missing_dependencies),
            file=sys.stderr,
        )
        return 1

    print("Matrix environment is ready.")
    return 0


def build_dashboard() -> int:
    npm_command = "npm.cmd" if os.name == "nt" else "npm"
    result = subprocess.run(
        [npm_command, "run", "build"],
        cwd=ROOT / "dashboard",
        check=False,
    )
    return result.returncode


def run_engine(bus_url: str | None) -> int:
    if bus_url:
        os.environ["ZMQ_BUS_URL"] = bus_url
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    from matrix_main import boot_matrix

    try:
        asyncio.run(boot_matrix())
    except KeyboardInterrupt:
        print("Matrix engine stopped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "check":
        return check_environment()
    if args.command == "dashboard-build":
        return build_dashboard()
    if args.command == "run":
        return run_engine(args.bus_url)
    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

