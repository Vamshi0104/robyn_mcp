from __future__ import annotations

import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from robyn_mcp.cli import main
from robyn_mcp.testing.endpoint_validator import EndpointValidator


class _MockResponse:
    def __init__(self, status: int, headers: dict[str, str], payload: dict):
        self.status = status
        self.headers = headers
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_endpoint_validator_happy_path(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=5.0):
        calls.append((req.get_method(), req.full_url, dict(req.header_items()), req.data))
        method = req.get_method()
        if method == "GET":
            return _MockResponse(200, {}, {"name": "demo", "protocolVersion": "2025-11-25", "capabilities": {"tools": {}}})
        body = json.loads(req.data.decode("utf-8"))
        if body["method"] == "initialize":
            return _MockResponse(200, {"mcp-session-id": "abc", "mcp-protocol-version": "2025-11-25"}, {"jsonrpc": "2.0", "id": 1, "result": {}})
        return _MockResponse(200, {}, {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "ping"}, {"name": "echo"}]}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    report = EndpointValidator("http://localhost:8000/mcp").validate()
    assert report.ok is True
    assert report.session_id == "abc"
    assert report.tool_count == 2
    assert report.steps[-1].payload["toolNames"] == ["ping", "echo"]
    assert len(calls) == 3


def test_endpoint_validator_failure_returns_report(monkeypatch):
    def fake_urlopen(req, timeout=5.0):
        raise HTTPError(req.full_url, 500, "boom", hdrs={}, fp=io.BytesIO(b'{"error": true}'))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    report = EndpointValidator("http://localhost:8000/mcp").validate()
    assert report.ok is False
    assert report.steps[0].name == "metadata"


def test_cli_runtime_json(capsys):
    exit_code = main(["runtime", "--json"])
    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert "runtime_status" in out


def test_cli_validate_endpoint(monkeypatch, capsys):
    monkeypatch.setattr(
        "robyn_mcp.cli.EndpointValidator",
        lambda endpoint, timeout=5.0: SimpleNamespace(validate=lambda: SimpleNamespace(as_dict=lambda: {"endpoint": endpoint, "ok": True})),
    )
    exit_code = main(["validate-endpoint", "http://localhost:8000/mcp", "--json"])
    assert exit_code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
