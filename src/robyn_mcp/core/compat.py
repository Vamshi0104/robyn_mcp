from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from robyn_mcp.core.config import RobynMCPConfig


def _safe_version(package_name: str) -> str | None:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None


def build_compatibility_report(config: RobynMCPConfig) -> dict[str, Any]:
    robyn_version = _safe_version("robyn")
    supported_protocols = ["2025-03-26", "2025-06-18", config.protocol_version]
    client_matrix = [
        {
            "client": "Claude Desktop",
            "stdio": "planned",
            "streamable_http": "not_applicable",
            "auth": "configurable",
            "tools": "contract",
            "resources": "contract",
            "prompts": "contract",
        },
        {
            "client": "Claude Code",
            "stdio": "planned",
            "streamable_http": "contract",
            "auth": "configurable",
            "tools": "contract",
            "resources": "contract",
            "prompts": "contract",
        },
        {
            "client": "ChatGPT",
            "stdio": "not_applicable",
            "streamable_http": "contract",
            "auth": "configurable",
            "tools": "contract",
            "resources": "contract",
            "prompts": "needs_repeatable_test",
        },
        {
            "client": "Cursor",
            "stdio": "planned",
            "streamable_http": "contract",
            "auth": "configurable",
            "tools": "contract",
            "resources": "contract",
            "prompts": "needs_repeatable_test",
        },
        {
            "client": "VS Code",
            "stdio": "planned",
            "streamable_http": "contract",
            "auth": "configurable",
            "tools": "contract",
            "resources": "contract",
            "prompts": "needs_repeatable_test",
        },
        {
            "client": "MCP Inspector",
            "stdio": "planned",
            "streamable_http": "contract",
            "auth": "configurable",
            "tools": "contract",
            "resources": "contract",
            "prompts": "contract",
        },
    ]
    return {
        "robyn_mcp": config.version,
        "mcp_protocol_version": config.protocol_version,
        "supported_protocol_versions": supported_protocols,
        "python_runtime": sys.version.split()[0],
        "python_packages": {"robyn": robyn_version, "pydantic": _safe_version("pydantic")},
        "runtime_status": {
            "robyn_installed": robyn_version is not None,
            "validation_mode": "live" if robyn_version is not None else "contract-only",
            "compatibility_tier": "validated" if robyn_version else "contract-only",
        },
        "transports": {
            "http": True,
            "streamable_http": True,
            "stateless_http": not config.require_session,
            "stateful_http": config.require_session,
            "stdio": False,
            "legacy_sse": config.enable_legacy_sse,
        },
        "protocol_checks": {
            "initialize_lifecycle": True,
            "capability_negotiation": True,
            "client_information": True,
            "server_information": True,
            "tools_capability": True,
            "resources_capability": config.enable_resources,
            "prompts_capability": config.enable_prompts,
            "logging_capability": False,
            "progress_notifications": False,
            "cancellation_notifications": False,
            "structured_tool_output": True,
            "jsonrpc_error_mapping": True,
            "invalid_request_handling": True,
            "batch_requests": False,
            "session_creation": True,
            "session_expiration": True,
            "session_deletion": True,
            "http_status_semantics": True,
            "origin_validation": config.allowed_origins is not None or not config.allow_no_origin,
            "content_type_validation": True,
            "authentication_challenges": False,
            "graceful_shutdown": False,
        },
        "features": {
            "tools": True,
            "resources": config.enable_resources,
            "prompts": config.enable_prompts,
            "header_forwarding": True,
            "cookie_forwarding": bool(config.forwarded_cookies),
            "rate_limiting": config.rate_limit_enabled,
            "audit_log": config.enable_audit_log,
            "metrics": config.enable_metrics,
            "response_cache": config.enable_response_cache,
            "response_redaction": bool(config.redact_response_fields),
            "openapi_ref_resolution": config.resolve_openapi_refs,
            "header_parameter_schema": config.include_header_parameters_in_schema,
            "openapi_operation_source": True,
            "least_privilege_recommendations": True,
        },
        "openapi_harvesting": {
            "preferred_content_types": list(config.prefer_openapi_body_content_types),
            "include_header_parameters": config.include_header_parameters_in_schema,
            "resolve_refs": config.resolve_openapi_refs,
        },
        "tested_matrix_hint": {
            "robyn_latest_known_from_docs": "0.79.0",
            "mcp_specs": supported_protocols,
            "python": [sys.version.split()[0]],
        },
        "client_compatibility_matrix": client_matrix,
    }
