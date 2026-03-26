from __future__ import annotations

from robyn_mcp import RobynMCP, RobynMCPConfig
from robyn_mcp.cli import main
from robyn_mcp.install_notice import build_install_banner


class _FakeApp:
    def __init__(self) -> None:
        self.routes = []
        self.start_calls = 0

    def start(self, **kwargs):
        self.start_calls += 1
        return kwargs


class _ReadonlyStartApp:
    __slots__ = ("routes", "start_calls")

    def __init__(self) -> None:
        self.routes = []
        self.start_calls = 0

    def start(self, **kwargs):
        self.start_calls += 1
        return kwargs


def test_install_banner_contains_release_metadata() -> None:
    banner = build_install_banner()
    assert "ROBYN-MCP" in banner
    assert "Vamshi Krishna Madhavan" in banner
    assert "Apache-2.0" in banner
    assert "Mar 22, 2026" in banner


def test_install_note_cli_prints_banner(capsys) -> None:
    assert main(["install-note"]) == 0
    out = capsys.readouterr().out
    assert "ROBYN-MCP" in out


def test_runtime_banner_prints_when_app_starts(capsys) -> None:
    app = _FakeApp()
    RobynMCP(app, config=RobynMCPConfig(require_session=False))
    app.start(port=8080)
    out = capsys.readouterr().out
    assert "ROBYN-MCP" in out
    assert "Author : Vamshi Krishna Madhavan" in out


def test_runtime_banner_can_be_disabled(capsys) -> None:
    app = _FakeApp()
    RobynMCP(app, config=RobynMCPConfig(require_session=False, show_banner_on_start=False))
    app.start(port=8080)
    out = capsys.readouterr().out
    assert "ROBYN-MCP" not in out


def test_runtime_banner_fallback_when_start_is_not_writable(capsys) -> None:
    app = _ReadonlyStartApp()
    RobynMCP(app, config=RobynMCPConfig(require_session=False))
    out = capsys.readouterr().out
    assert "ROBYN-MCP" in out
    app.start(port=8080)
    out_after_start = capsys.readouterr().out
    assert "ROBYN-MCP" not in out_after_start
