from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ValidationStep:
    name: str
    ok: bool
    detail: str
    payload: dict[str, Any] | None = None


@dataclass(slots=True)
class EndpointValidationReport:
    endpoint: str
    ok: bool
    protocol_version: str | None = None
    session_id: str | None = None
    server_name: str | None = None
    tool_count: int | None = None
    steps: list[ValidationStep] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "ok": self.ok,
            "protocol_version": self.protocol_version,
            "session_id": self.session_id,
            "server_name": self.server_name,
            "tool_count": self.tool_count,
            "steps": [
                {
                    "name": step.name,
                    "ok": step.ok,
                    "detail": step.detail,
                    "payload": step.payload,
                }
                for step in self.steps
            ],
        }

    def fetch_tools(self) -> list[dict[str, Any]]:
        return list(self.tools)


class EndpointValidator:
    def __init__(self, endpoint: str, *, timeout: float = 5.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def _open(
        self,
        method: str,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], Any]:
        data = None
        final_headers = dict(headers or {})
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            final_headers.setdefault("content-type", "application/json")
        req = urllib.request.Request(self.endpoint, data=data, method=method.upper(), headers=final_headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                try:
                    parsed = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    parsed = {"raw": raw}
                return resp.status, {k.lower(): v for k, v in resp.headers.items()}, parsed
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"raw": raw}
            return exc.code, {k.lower(): v for k, v in exc.headers.items()}, parsed

    def validate(self) -> EndpointValidationReport:
        steps: list[ValidationStep] = []
        session_id: str | None = None
        protocol_version: str | None = None
        server_name: str | None = None
        tool_count: int | None = None
        tools: list[dict[str, Any]] = []

        status, headers, payload = self._open("GET", {"accept": "application/json"})
        metadata_ok = status == 200 and isinstance(payload, dict) and payload.get("capabilities")
        server_name = payload.get("name") if isinstance(payload, dict) else None
        protocol_version = payload.get("protocolVersion") if isinstance(payload, dict) else None
        steps.append(
            ValidationStep(
                name="metadata",
                ok=metadata_ok,
                detail=f"GET returned {status}",
                payload=payload if isinstance(payload, dict) else None,
            )
        )
        if not metadata_ok:
            return EndpointValidationReport(
                endpoint=self.endpoint,
                ok=False,
                protocol_version=protocol_version,
                server_name=server_name,
                steps=steps,
            )

        status, headers, payload = self._open(
            "POST",
            {"accept": "application/json", "content-type": "application/json"},
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "robyn-mcp-validator", "version": "0.16.0"},
                    "capabilities": {},
                },
            },
        )
        init_ok = status == 200 and isinstance(payload, dict) and "result" in payload
        session_id = headers.get("mcp-session-id")
        protocol_version = headers.get("mcp-protocol-version") or protocol_version
        steps.append(
            ValidationStep(
                name="initialize",
                ok=init_ok and session_id is not None,
                detail=f"POST initialize returned {status}",
                payload=payload if isinstance(payload, dict) else None,
            )
        )
        if not init_ok or not session_id:
            return EndpointValidationReport(
                endpoint=self.endpoint,
                ok=False,
                protocol_version=protocol_version,
                server_name=server_name,
                session_id=session_id,
                steps=steps,
            )

        status, headers, payload = self._open(
            "POST",
            {
                "accept": "application/json",
                "content-type": "application/json",
                "mcp-session-id": session_id,
                "mcp-protocol-version": protocol_version or "2025-11-25",
            },
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        tools = ((payload or {}).get("result") or {}).get("tools") if isinstance(payload, dict) else None
        tools = tools if isinstance(tools, list) else []
        tool_count = len(tools)
        list_ok = status == 200 and isinstance(tools, list)
        steps.append(
            ValidationStep(
                name="tools/list",
                ok=list_ok,
                detail=f"POST tools/list returned {status}",
                payload={
                    "toolCount": tool_count,
                    "toolNames": [item.get("name") for item in tools[:25]],
                },
            )
        )

        return EndpointValidationReport(
            endpoint=self.endpoint,
            ok=all(step.ok for step in steps),
            protocol_version=protocol_version,
            session_id=session_id,
            server_name=server_name,
            tool_count=tool_count,
            steps=steps,
            tools=tools,
        )
