from __future__ import annotations

from pathlib import Path
from runpy import run_path

from setuptools import setup
from setuptools.command.install import install


def _load_install_banner() -> str:
    notice_path = Path(__file__).resolve().parent / "src" / "robyn_mcp" / "install_notice.py"
    namespace = run_path(str(notice_path))
    builder = namespace.get("build_install_banner")
    if callable(builder):
        try:
            return str(builder())
        except Exception:
            return "ROBYN-MCP"
    return "ROBYN-MCP"


class _InstallWithBanner(install):
    def run(self) -> None:
        super().run()
        print()
        print(_load_install_banner())


setup(cmdclass={"install": _InstallWithBanner})
