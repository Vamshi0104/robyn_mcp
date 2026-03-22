
from __future__ import annotations

from robyn_mcp.core.models import RouteMetadata

_INJECTION_MARKERS = ("ignore previous instructions", "system prompt", "jailbreak", "<tool>", "</tool>")


def _sanitize_human_text(value: str) -> str:
    text = " ".join(value.strip().split())
    lowered = text.lower()
    for marker in _INJECTION_MARKERS:
        lowered = lowered.replace(marker, "")
    if len(text) > 400:
        text = text[:397].rstrip() + "..."
    return text


def build_tool_description(meta: RouteMetadata) -> str:
    parts: list[str] = []
    primary = meta.human_summary or meta.summary or meta.description or f"Call {meta.method.upper()} {meta.path}."
    parts.append(_sanitize_human_text(primary))

    operation_kind = "read" if not meta.side_effect else "action"
    parts.append(f"Tool type: {operation_kind}.")
    parts.append(f"HTTP route: {meta.method.upper()} {meta.path}.")

    if meta.requires_auth:
        if meta.required_permissions:
            parts.append(f"Permissions required: {', '.join(meta.required_permissions)}.")
        elif meta.auth_scopes:
            parts.append(f"Scopes required: {', '.join(meta.auth_scopes)}.")
        else:
            parts.append("Authentication required.")

    if meta.idempotent is True:
        parts.append("Retry behavior: idempotent.")
    elif meta.idempotent is False:
        parts.append("Retry behavior: non-idempotent; avoid duplicate execution.")
    if meta.side_effect:
        parts.append("Side effects: yes.")
    else:
        parts.append("Side effects: no.")
    if meta.tags:
        parts.append(f"Tags: {', '.join(meta.tags)}.")
    if meta.examples:
        example_names = ", ".join(example.get("name", "example") for example in meta.examples[:3])
        parts.append(f"Examples available: {example_names}.")
    return " ".join(parts)
