from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def run(cmd: list[str], **kwargs) -> None:
    subprocess.run(cmd, check=True, **kwargs)


if __name__ == "__main__":
    wheel = next(iter(sorted(DIST.glob("*.whl"))), None)
    if wheel is None:
        raise SystemExit("No wheel found. Run python -m build first.")

    with tempfile.TemporaryDirectory() as td:
        py = Path(td) / ("Scripts/python.exe" if sys.platform.startswith("win") else "bin/python")
        run([sys.executable, "-m", "venv", td])
        run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(py), "-m", "pip", "install", str(wheel)])
        run([str(py), "-m", "robyn_mcp.cli", "install-note"])
        run([str(py), "-c", "import robyn_mcp; print(robyn_mcp.__all__)"])
    print("Install verification passed")
