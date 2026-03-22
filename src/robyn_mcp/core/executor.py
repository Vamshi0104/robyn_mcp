from __future__ import annotations

import inspect
import json
import time
from typing import Any


def _truncate_preview(value: object, max_chars: int) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        raw = str(value)
    return raw if len(raw) <= max_chars else raw[: max_chars - 3] + "..."


class ToolExecutor:
    """
    Backward-compatible executor.

    Old server code creates it like:
        ToolExecutor(policy, metrics=self.metrics)

    Newer code may still use it for tracing.
    """

    def __init__(self, policy: Any, metrics: Any | None = None):
        self.policy = policy
        self.metrics = metrics
        self.config = getattr(policy, "config", None)

    async def execute(
        self,
        *,
        tool_name: str,
        handler: Any,
        arguments: dict[str, Any],
        context: Any,
    ) -> Any:
        started = time.perf_counter()
        result = None
        error_message = None

        try:
            await self.policy.authorize_tool(tool_name, context)

            call_kwargs = dict(arguments or {})
            try:
                sig = inspect.signature(handler)
                if "request" in sig.parameters:
                    call_kwargs["request"] = context
            except Exception:
                pass

            if inspect.iscoroutinefunction(handler):
                result = await handler(**call_kwargs)
            else:
                result = handler(**call_kwargs)

            if self.metrics is not None:
                if getattr(self.config, "enable_tool_tracing", False):
                    arguments_preview = None
                    result_preview = None

                    if getattr(self.config, "trace_include_arguments", False):
                        arguments_preview = _truncate_preview(
                            arguments, getattr(self.config, "trace_max_argument_chars", 512)
                        )
                    if getattr(self.config, "trace_include_result_preview", False):
                        result_preview = _truncate_preview(
                            result, getattr(self.config, "trace_max_result_chars", 512)
                        )

                    if hasattr(self.metrics, "record_tool_call"):
                        self.metrics.record_tool_call(
                            tool_name=tool_name,
                            status="ok",
                            duration_ms=(time.perf_counter() - started) * 1000.0,
                            session_id=getattr(context, "session_id", None),
                            tenant_id=getattr(context, "tenant_id", None),
                            principal_id=getattr(context, "principal_id", None),
                            request_id=(getattr(context, "headers", {}) or {}).get("x-request-id"),
                            arguments_preview=arguments_preview,
                            result_preview=result_preview,
                            error_message=None,
                        )
                elif hasattr(self.metrics, "record_success"):
                    self.metrics.record_success(
                        tool_name,
                        (time.perf_counter() - started) * 1000.0,
                        context,
                    )

            return result

        except Exception as exc:
            error_message = str(exc)

            if self.metrics is not None:
                if getattr(self.config, "enable_tool_tracing", False):
                    arguments_preview = None
                    if getattr(self.config, "trace_include_arguments", False):
                        arguments_preview = _truncate_preview(
                            arguments, getattr(self.config, "trace_max_argument_chars", 512)
                        )

                    if hasattr(self.metrics, "record_tool_call"):
                        self.metrics.record_tool_call(
                            tool_name=tool_name,
                            status="error",
                            duration_ms=(time.perf_counter() - started) * 1000.0,
                            session_id=getattr(context, "session_id", None),
                            tenant_id=getattr(context, "tenant_id", None),
                            principal_id=getattr(context, "principal_id", None),
                            request_id=(getattr(context, "headers", {}) or {}).get("x-request-id"),
                            arguments_preview=arguments_preview,
                            result_preview=None,
                            error_message=error_message,
                        )
                elif hasattr(self.metrics, "record_error"):
                    self.metrics.record_error(
                        tool_name,
                        (time.perf_counter() - started) * 1000.0,
                        context,
                        error_message,
                    )

            raise