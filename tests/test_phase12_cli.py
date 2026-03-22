from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from robyn_mcp.cli import main


def test_cli_inspect_json(monkeypatch, capsys):
    class _Report:
        ok = True
        def as_dict(self):
            return {"endpoint": "http://localhost:8000/mcp", "ok": True}
        def fetch_tools(self):
            return [{"name": "ping", "annotations": {"readOnlyHint": True}}]

    monkeypatch.setattr("robyn_mcp.cli.EndpointValidator", lambda endpoint, timeout=5.0: SimpleNamespace(validate=lambda: _Report()))
    exit_code = main(["inspect", "http://localhost:8000/mcp", "--json"])
    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["summary"]["toolNames"] == ["ping"]
    assert out["summary"]["readOnlyTools"] == ["ping"]


def test_cli_debug_snapshot_writes_file(monkeypatch, tmp_path):
    class _Report:
        ok = True
        def as_dict(self):
            return {"endpoint": "http://localhost:8000/mcp", "ok": True}
        def fetch_tools(self):
            return [{"name": "ping"}]

    monkeypatch.setattr("robyn_mcp.cli.EndpointValidator", lambda endpoint, timeout=5.0: SimpleNamespace(validate=lambda: _Report()))
    target = tmp_path / "snapshot.json"
    exit_code = main(["debug-snapshot", "http://localhost:8000/mcp", "--out", str(target)])
    assert exit_code == 0
    payload = json.loads(target.read_text())
    assert payload["tools"][0]["name"] == "ping"


def test_endpoint_report_fetch_tools_roundtrip():
    from robyn_mcp.testing.endpoint_validator import EndpointValidationReport

    report = EndpointValidationReport(endpoint="http://x", ok=True, tools=[{"name": "a"}])
    assert report.fetch_tools() == [{"name": "a"}]
