from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class RobynMCPConfig(BaseModel):
    # Core identity
    name: str = "robyn-mcp"
    server_name: str = "robyn-mcp"
    description: str = "Robyn MCP server"
    version: str = "1.0.0"

    # Protocol
    protocol_version: str = "2025-11-25"
    supported_protocol_versions: list[str] = Field(
        default_factory=lambda: ["2025-03-26", "2025-06-18", "2025-11-25"]
    )

    # Transport / endpoint
    mcp_path: str = "/mcp"
    playground_path: str = "/mcp/playground"
    require_session: bool = True
    require_accept_header: bool = False
    allow_no_origin: bool = True
    allowed_origins: set[str] | None = None
    enable_legacy_sse: bool = False
    session_ttl_seconds: int = 3600

    # Safe publish defaults
    enable_resources: bool = False
    enable_prompts: bool = False
    auto_expose_openapi: bool = False
    enable_playground: bool = False
    enable_tool_tracing: bool = True

    # Core operational features
    enable_metrics: bool = True
    enable_audit_log: bool = True
    include_server_instructions: bool = False
    instructions: str | None = None

    # Filtering
    include_tags: set[str] | None = None
    exclude_tags: set[str] | None = None
    include_operations: set[str] | None = None
    exclude_operations: set[str] | None = None

    # Auth / claims
    principal_header: str = "x-auth-sub"
    tenant_header: str = "x-tenant-id"
    client_id_header: str = "x-client-id"
    auth_scopes_header: str = "x-auth-scopes"
    scopes_header_names: list[str] = Field(
        default_factory=lambda: ["x-auth-scopes", "x-scopes", "authorization-scopes"]
    )
    principal_claim_keys: list[str] = Field(default_factory=lambda: ["sub", "user_id", "uid"])
    tenant_claim_keys: list[str] = Field(default_factory=lambda: ["tenant_id", "tid"])
    client_claim_keys: list[str] = Field(default_factory=lambda: ["client_id", "azp"])
    client_id_claim_keys: list[str] = Field(default_factory=lambda: ["client_id", "azp"])
    scope_claim_keys: list[str] = Field(default_factory=lambda: ["scope", "scp", "scopes"])

    # Response / redaction
    redact_response_fields: set[str] = Field(default_factory=set)

    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_scope: str = "session"
    rate_limit_capacity: int = 60
    rate_limit_refill_per_second: float = 1.0

    # Publishing
    max_tools_per_page: int = 200
    publish_examples_in_tool_description: bool = False

    # Forwarding
    forwarded_headers: set[str] = Field(
        default_factory=lambda: {
            "authorization",
            "x-tenant-id",
            "x-auth-sub",
            "x-client-id",
            "x-request-id",
            "origin",
            "x-auth-scopes",
        }
    )
    forwarded_cookies: set[str] = Field(default_factory=set)

    # OpenAPI harvesting
    prefer_openapi_body_content_types: list[str] = Field(
        default_factory=lambda: [
            "application/json",
            "application/merge-patch+json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ]
    )
    include_header_parameters_in_schema: bool = False
    resolve_openapi_refs: bool = True

    # OpenAPI auto-generation
    auto_expose_safe_get_as_tools: bool = True
    auto_expose_mutations_as_tools: bool = True
    auto_expose_resources_from_get: bool = False
    auto_expose_tag_allowlist: set[str] | None = None
    auto_expose_tag_denylist: set[str] | None = None
    auto_expose_operation_allowlist: set[str] | None = None
    auto_expose_operation_denylist: set[str] | None = None
    auto_generated_tool_prefix: str | None = None
    auto_generated_description_suffix: str = "Auto-generated from OpenAPI."

    # Tracing
    trace_include_arguments: bool = False
    trace_include_result_preview: bool = False
    trace_max_argument_chars: int = 512
    trace_max_result_chars: int = 512
    metrics_window_size: int = 2048

    @model_validator(mode="after")
    def validate_filters(self) -> "RobynMCPConfig":
        if not self.mcp_path.startswith("/"):
            raise ValueError("mcp_path must start with '/'")
        if not self.playground_path.startswith("/"):
            raise ValueError("playground_path must start with '/'")
        if self.trace_max_argument_chars <= 0:
            raise ValueError("trace_max_argument_chars must be > 0")
        if self.trace_max_result_chars <= 0:
            raise ValueError("trace_max_result_chars must be > 0")
        if self.metrics_window_size <= 0:
            raise ValueError("metrics_window_size must be > 0")
        if self.auto_expose_tag_allowlist and self.auto_expose_tag_denylist:
            raise ValueError("auto_expose_tag_allowlist and auto_expose_tag_denylist cannot be used together")
        if self.auto_expose_operation_allowlist and self.auto_expose_operation_denylist:
            raise ValueError("auto_expose_operation_allowlist and auto_expose_operation_denylist cannot be used together")
        return self

    def metadata_payload(self) -> dict[str, Any]:
        return {
            "name": self.name or self.server_name,
            "version": self.version,
            "protocolVersion": self.protocol_version,
            "endpoint": self.mcp_path,
        }