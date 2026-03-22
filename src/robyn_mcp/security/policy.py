
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.security.rate_limit import RateLimitExceeded, TokenBucketLimiter


@dataclass(slots=True)
class RequestContext:
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    client_id: str | None = None
    tenant_id: str | None = None
    principal: Any = None
    principal_id: str | None = None
    scopes: set[str] = field(default_factory=set)
    claims: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    protocol_version: str | None = None
    origin: str | None = None
    raw_request: Any = None


def _redact_value(value: Any, redact_fields: set[str]) -> Any:
    if not redact_fields:
        return value
    if isinstance(value, dict):
        return {key: ("***REDACTED***" if str(key) in redact_fields else _redact_value(item, redact_fields)) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item, redact_fields) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item, redact_fields) for item in value)
    return value


class PolicyEngine:
    def __init__(self, config: RobynMCPConfig | None = None) -> None:
        self.config = config or RobynMCPConfig()
        self._limiter = TokenBucketLimiter(capacity=self.config.rate_limit_capacity, refill_per_second=self.config.rate_limit_refill_per_second) if self.config.rate_limit_enabled else None

    def _rate_limit_key(self, tool_name: str, context: RequestContext) -> str:
        scope = self.config.rate_limit_scope
        if scope == "principal":
            return f"{tool_name}:principal:{context.principal_id or 'anonymous'}"
        if scope == "client":
            return f"{tool_name}:client:{context.client_id or 'unknown'}"
        if scope == "global":
            return f"{tool_name}:global"
        return f"{tool_name}:session:{context.session_id or 'none'}"

    async def authorize_tool(self, tool_name: str, context: RequestContext) -> None:
        if self._limiter is not None:
            try:
                self._limiter.consume(self._rate_limit_key(tool_name, context))
            except RateLimitExceeded as exc:
                raise PermissionError(str(exc)) from exc

    async def before_call(self, tool_name: str, arguments: dict[str, Any], context: RequestContext) -> None:
        return None

    async def after_call(self, tool_name: str, result: Any, context: RequestContext) -> Any:
        return _redact_value(result, self.config.redact_response_fields)

    async def authorize_resource(self, uri: str, context: RequestContext) -> None:
        return await self.authorize_tool(f"resource:{uri}", context)

    async def authorize_prompt(self, name: str, context: RequestContext) -> None:
        return await self.authorize_tool(f"prompt:{name}", context)


class ScopedPolicyEngine(PolicyEngine):
    def __init__(self, required_scopes: dict[str, set[str]], config: RobynMCPConfig | None = None) -> None:
        super().__init__(config=config)
        self.required_scopes = required_scopes

    async def authorize_tool(self, tool_name: str, context: RequestContext) -> None:
        await super().authorize_tool(tool_name, context)
        required = self.required_scopes.get(tool_name, set())
        if required and not required.issubset(context.scopes):
            missing = sorted(required - context.scopes)
            raise PermissionError(f"Missing scopes for tool '{tool_name}': {', '.join(missing)}")
