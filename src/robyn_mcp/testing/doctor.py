from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from robyn_mcp.testing.endpoint_validator import EndpointValidator


@dataclass(slots=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


@dataclass(slots=True)
class DoctorReport:
    endpoint: str
    ok: bool
    score: int
    checks: list[DoctorCheck] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "ok": self.ok,
            "score": self.score,
            "checks": [
                {"name": check.name, "status": check.status, "detail": check.detail}
                for check in self.checks
            ],
        }


def run_doctor(endpoint: str, *, timeout: float = 5.0) -> DoctorReport:
    validator = EndpointValidator(endpoint, timeout=timeout)
    validation = validator.validate()
    checks: list[DoctorCheck] = [
        DoctorCheck(
            name=step.name,
            status="PASS" if step.ok else "FAIL",
            detail=step.detail,
        )
        for step in validation.steps
    ]

    step_names = {step.name for step in validation.steps if step.ok}
    metadata = validation.steps[0].payload if validation.steps else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    checks.append(
        DoctorCheck(
            name="protocol",
            status="PASS" if validation.protocol_version else "WARN",
            detail=validation.protocol_version or "Protocol version was not reported.",
        )
    )
    checks.append(
        DoctorCheck(
            name="capability negotiation",
            status="PASS" if "initialize" in step_names else "FAIL",
            detail="initialize completed with an MCP session."
            if "initialize" in step_names
            else "initialize did not complete successfully.",
        )
    )
    checks.append(
        DoctorCheck(
            name="tool discovery",
            status="PASS" if validation.tool_count is not None else "FAIL",
            detail=f"{validation.tool_count or 0} tools discovered.",
        )
    )
    if validation.session_id:
        status, _headers, payload = validator._open(
            "POST",
            {
                "accept": "application/json",
                "content-type": "application/json",
                "mcp-session-id": validation.session_id,
                "mcp-protocol-version": validation.protocol_version or "2025-11-25",
            },
            {"jsonrpc": "2.0", "id": 90, "method": "robyn_mcp/definitely_missing", "params": {}},
        )
        error_code = (
            ((payload or {}).get("error") or {}).get("code") if isinstance(payload, dict) else None
        )
        checks.append(
            DoctorCheck(
                name="unknown method error mapping",
                status="PASS" if status == 404 and error_code == -32601 else "FAIL",
                detail=f"unknown method returned HTTP {status}, JSON-RPC code {error_code}",
            )
        )

        status, _headers, payload = validator._open(
            "POST",
            {
                "accept": "application/json",
                "content-type": "application/json",
                "mcp-session-id": validation.session_id,
                "mcp-protocol-version": "1900-01-01",
            },
            {"jsonrpc": "2.0", "id": 91, "method": "tools/list", "params": {}},
        )
        checks.append(
            DoctorCheck(
                name="unsupported protocol rejection",
                status="PASS" if status == 400 else "FAIL",
                detail=f"unsupported protocol request returned HTTP {status}",
            )
        )

        status, _headers, _payload = validator._open(
            "DELETE",
            {"accept": "application/json", "mcp-session-id": validation.session_id},
        )
        checks.append(
            DoctorCheck(
                name="session deletion",
                status="PASS" if status in {200, 204} else "WARN",
                detail=f"DELETE session returned HTTP {status}",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                name="negative protocol checks",
                status="WARN",
                detail="Skipped because initialize did not produce a session.",
            )
        )

    compatibility = metadata.get("compatibility") if isinstance(metadata, dict) else {}
    protocol_checks = (
        compatibility.get("protocol_checks") if isinstance(compatibility, dict) else {}
    )
    if isinstance(protocol_checks, dict):
        missing = sorted(name for name, enabled in protocol_checks.items() if enabled is False)
        checks.append(
            DoctorCheck(
                name="protocol coverage",
                status="WARN" if missing else "PASS",
                detail="Missing or planned checks: " + ", ".join(missing[:8])
                if missing
                else "All advertised protocol checks are enabled.",
            )
        )
    checks.append(
        DoctorCheck(
            name="structured output",
            status="WARN",
            detail="Run integration tests against real tool calls to verify output schemas.",
        )
    )
    checks.append(
        DoctorCheck(
            name="security",
            status="WARN",
            detail=(
                "Verify origin policy, auth challenges, header allowlists, and tenant "
                "isolation before production."
            ),
        )
    )

    passing = sum(1 for check in checks if check.status == "PASS")
    warning = sum(1 for check in checks if check.status == "WARN")
    score = max(0, min(100, int((passing / max(len(checks), 1)) * 100 - warning * 2)))
    ok = validation.ok and all(check.status != "FAIL" for check in checks)
    return DoctorReport(endpoint=endpoint, ok=ok, score=score, checks=checks)
