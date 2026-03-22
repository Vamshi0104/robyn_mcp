
from __future__ import annotations

from collections.abc import Callable
from typing import Any


ROB_MCP_META = "__robyn_mcp__"
ROB_MCP_RESOURCE_META = "__robyn_mcp_resource__"
ROB_MCP_PROMPT_META = "__robyn_mcp_prompt__"


def expose_tool(
    *,
    operation_id: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    human_summary: str | None = None,
    tags: list[str] | None = None,
    requires_auth: bool = False,
    side_effect: bool = False,
    idempotent: bool | None = None,
    exposed: bool = True,
    auth_scopes: list[str] | None = None,
    required_permissions: list[str] | None = None,
    examples: list[dict[str, Any]] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(
            func,
            ROB_MCP_META,
            {
                "operation_id": operation_id,
                "summary": summary,
                "description": description,
                "human_summary": human_summary,
                "tags": tags or [],
                "requires_auth": requires_auth,
                "side_effect": side_effect,
                "idempotent": idempotent,
                "exposed": exposed,
                "auth_scopes": auth_scopes or [],
                "required_permissions": required_permissions or [],
                "examples": examples or [],
            },
        )
        return func

    return decorator


def expose_resource(
    *,
    uri: str,
    name: str | None = None,
    description: str | None = None,
    mime_type: str = "application/json",
    tags: list[str] | None = None,
    requires_auth: bool = False,
    annotations: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(
            func,
            ROB_MCP_RESOURCE_META,
            {
                "uri": uri,
                "name": name or func.__name__,
                "description": description,
                "mime_type": mime_type,
                "tags": tags or [],
                "requires_auth": requires_auth,
                "annotations": annotations or {},
            },
        )
        return func

    return decorator


def expose_prompt(
    *,
    name: str | None = None,
    title: str | None = None,
    description: str | None = None,
    arguments: list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
    requires_auth: bool = False,
    annotations: dict[str, Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(
            func,
            ROB_MCP_PROMPT_META,
            {
                "name": name or func.__name__,
                "title": title,
                "description": description,
                "arguments": arguments or [],
                "tags": tags or [],
                "requires_auth": requires_auth,
                "annotations": annotations or {},
            },
        )
        return func

    return decorator
