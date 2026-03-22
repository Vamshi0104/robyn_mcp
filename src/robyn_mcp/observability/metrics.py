from __future__ import annotations

import time
from collections import Counter, deque
from typing import Any

from robyn_mcp.core.models import ToolTraceEvent


class MetricsCollector:
    def __init__(self, audit_window_size: int = 256, config: Any | None = None):
        self.config = config
        self.audit_window_size = audit_window_size
        self._audit_events = deque(maxlen=audit_window_size)

        window = getattr(config, "metrics_window_size", 2048) if config is not None else 2048
        self._tool_events = deque(maxlen=window)
        self._tool_counts = Counter()
        self._tool_errors = Counter()
        self._tool_latency_ms = Counter()
        self._counters = Counter()

    # older generic counter API
    def increment(self, name: str, amount: int = 1) -> None:
        self._counters[name] += amount

    def counter(self, name: str) -> int:
        return int(self._counters.get(name, 0))

    def record_error(self, tool_name: str, duration_ms: float, context: Any | None = None, error_message: str | None = None) -> None:
        self.record_failure(tool_name, duration_ms, context, error_message)

    # older success/failure API used by existing tests
    def record_success(self, tool_name: str, duration_ms: float, context: Any | None = None) -> None:
        self.record_tool_call(
            tool_name=tool_name,
            status="ok",
            duration_ms=duration_ms,
            session_id=getattr(context, "session_id", None),
            tenant_id=getattr(context, "tenant_id", None),
            principal_id=getattr(context, "principal_id", None),
        )

    def record_failure(self, tool_name: str, duration_ms: float, context: Any | None = None, error_message: str | None = None) -> None:
        self.record_tool_call(
            tool_name=tool_name,
            status="error",
            duration_ms=duration_ms,
            session_id=getattr(context, "session_id", None),
            tenant_id=getattr(context, "tenant_id", None),
            principal_id=getattr(context, "principal_id", None),
            error_message=error_message,
        )

    def record_audit_event(self, name: str, payload: dict[str, Any] | None = None) -> None:
        self._audit_events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "payload": payload or {},
            }
        )

    def recent_audit_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._audit_events)[-limit:]

    def record_tool_call(
        self,
        *,
        tool_name: str,
        status: str,
        duration_ms: float,
        session_id: str | None = None,
        tenant_id: str | None = None,
        principal_id: str | None = None,
        request_id: str | None = None,
        arguments_preview: str | None = None,
        result_preview: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self._tool_counts[tool_name] += 1
        self._tool_latency_ms[tool_name] += float(duration_ms)
        if status != "ok":
            self._tool_errors[tool_name] += 1

        self._tool_events.append(
            ToolTraceEvent(
                tool_name=tool_name,
                status=status,
                duration_ms=float(duration_ms),
                timestamp=time.time(),
                session_id=session_id,
                tenant_id=tenant_id,
                principal_id=principal_id,
                request_id=request_id,
                arguments_preview=arguments_preview,
                result_preview=result_preview,
                error_message=error_message,
            )
        )

    def tool_metrics_snapshot(self) -> dict[str, object]:
        tools: dict[str, dict[str, float | int]] = {}
        for name, count in self._tool_counts.items():
            total_latency = self._tool_latency_ms.get(name, 0.0)
            errors = self._tool_errors.get(name, 0)
            tools[name] = {
                "count": int(count),
                "errors": int(errors),
                "avgLatencyMs": (float(total_latency) / count) if count else 0.0,
            }
        return {"tools": tools}

    def recent_tool_events(self, limit: int = 20) -> list[dict[str, object]]:
        events = list(self._tool_events)[-limit:]
        return [
            {
                "toolName": e.tool_name,
                "status": e.status,
                "durationMs": e.duration_ms,
                "timestamp": e.timestamp,
                "sessionId": e.session_id,
                "tenantId": e.tenant_id,
                "principalId": e.principal_id,
                "requestId": e.request_id,
                "argumentsPreview": e.arguments_preview,
                "resultPreview": e.result_preview,
                "errorMessage": e.error_message,
            }
            for e in events
        ]

    def snapshot(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "counters": dict(self._counters),
            "auditEventCount": len(self._audit_events),
        }

        for name, count in self._tool_counts.items():
            payload[name] = {
                "calls": int(count),
                "errors": int(self._tool_errors.get(name, 0)),
                "avgLatencyMs": (
                    float(self._tool_latency_ms.get(name, 0.0)) / count
                    if count else 0.0
                ),
            }

        if self._tool_counts:
            payload["toolMetrics"] = self.tool_metrics_snapshot()

        return payload


MCPMetrics = MetricsCollector