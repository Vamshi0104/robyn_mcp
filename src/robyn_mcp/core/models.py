from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class RouteMetadata:
    path: str
    method: str
    handler: Callable[..., Any]
    operation_id: str
    summary: str | None = None
    description: str | None = None
    human_summary: str | None = None
    tags: list[str] = field(default_factory=list)
    requires_auth: bool = False
    side_effect: bool = False
    idempotent: bool | None = None
    exposed: bool = True
    auth_scopes: list[str] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    request_body_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    examples: list[dict[str, Any]] = field(default_factory=list)
    cache_ttl_seconds: int | None = None
    cache_tags: list[str] = field(default_factory=list)
    invalidate_tags: list[str] = field(default_factory=list)

    auto_generated: bool = False
    source: str = "decorator"
    openapi_tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ToolDefinition:
    name: str
    metadata: RouteMetadata
    title: str | None = None
    description: str | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    annotations: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ResourceDefinition:
    uri: str
    name: str
    handler: Callable[..., Any]
    description: str | None = None
    mime_type: str = "application/json"
    tags: list[str] = field(default_factory=list)
    requires_auth: bool = False
    annotations: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PromptArgument:
    name: str
    description: str | None = None
    required: bool = True


@dataclass(slots=True)
class PromptDefinition:
    name: str
    handler: Callable[..., Any]
    title: str | None = None
    description: str | None = None
    arguments: list[PromptArgument] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    requires_auth: bool = False
    annotations: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RequestContext:
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    client_id: str | None = None
    tenant_id: str | None = None
    principal: str | None = None
    principal_id: str | None = None
    scopes: list[str] = field(default_factory=list)
    claims: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    protocol_version: str | None = None
    origin: str | None = None
    raw_request: Any = None


@dataclass(slots=True)
class ToolTraceEvent:
    tool_name: str
    status: str
    duration_ms: float
    timestamp: float
    session_id: str | None = None
    tenant_id: str | None = None
    principal_id: str | None = None
    request_id: str | None = None
    arguments_preview: str | None = None
    result_preview: str | None = None
    error_message: str | None = None
