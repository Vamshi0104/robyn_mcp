from __future__ import annotations

import argparse
import subprocess
import sys
from importlib import metadata
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not-installed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upgrade pip, install robyn + robyn-mcp, print banner, and show installed versions."
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to use (default: current interpreter).",
    )
    parser.add_argument(
        "--wheel",
        default=None,
        help="Optional path to local robyn_mcp wheel. If omitted, installs robyn-mcp from index.",
    )
    args = parser.parse_args(argv)

    py = args.python
    run([py, "-m", "pip", "install", "--upgrade", "pip"])
    run([py, "-m", "pip", "install", "robyn"])

    if args.wheel:
        wheel = Path(args.wheel).expanduser().resolve()
        run([py, "-m", "pip", "install", str(wheel)])
    else:
        run([py, "-m", "pip", "install", "robyn-mcp"])

    run([py, "-m", "robyn_mcp.cli", "install-note"])

    print("Installed package versions:")
    print(f"pip: {package_version('pip')}")
    print(f"robyn: {package_version('robyn')}")
    print(f"robyn-mcp: {package_version('robyn-mcp')}")
    print(f"pydantic: {package_version('pydantic')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
