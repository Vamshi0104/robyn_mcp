
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
        "transports": {"http": True, "legacy_sse": config.enable_legacy_sse},
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
    }
