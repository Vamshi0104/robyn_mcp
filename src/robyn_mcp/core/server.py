from __future__ import annotations

import json
from typing import Any, Callable

from robyn_mcp.core.compat import build_compatibility_report
from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.core.describe import build_tool_description
from robyn_mcp.core.executor import ToolExecutor
from robyn_mcp.core.filters import FilterEngine
from robyn_mcp.core.introspect import extract_prompts, extract_resources, extract_routes
from robyn_mcp.core.response_cache import ToolResponseCache, normalize_tag
from robyn_mcp.core.models import PromptDefinition, ResourceDefinition, ToolDefinition
from robyn_mcp.core.naming import slugify_operation, unique_name
from robyn_mcp.observability.metrics import MetricsCollector
from robyn_mcp.playground.ui import build_playground_html
from robyn_mcp.schemas.json_schema import signature_to_input_schema
from robyn_mcp.security.auth import HeaderPrincipalResolver, PrincipalResolver
from robyn_mcp.security.policy import PolicyEngine, RequestContext
from robyn_mcp.transport.http import MCPDispatcher, MCPTransportError
from robyn_mcp.transport.protocol import INTERNAL_ERROR, jsonrpc_error, INVALID_REQUEST
from robyn_mcp.install_notice import build_install_banner

PARSE_ERROR = -32700

class RobynMCP:
    def __init__(
            self,
            app: Any,
            name: str | None = None,
            description: str | None = None,
            config: RobynMCPConfig | None = None,
            policy: PolicyEngine | None = None,
            principal_resolver: PrincipalResolver | None = None,
    ) -> None:
        self.app = app
        self.config = config or RobynMCPConfig(
            name=name or "robyn-mcp",
            description=description or "Robyn MCP server",
        )
        self.metrics = MetricsCollector(audit_window_size=self.config.metrics_window_size)
        self.policy = policy or PolicyEngine(config=self.config)
        self.principal_resolver = principal_resolver or HeaderPrincipalResolver()
        self.executor = ToolExecutor(self.policy, metrics=self.metrics)
        self.response_cache = ToolResponseCache(
            enabled=self.config.enable_response_cache,
            default_ttl_seconds=self.config.response_cache_ttl_seconds,
            max_entries=self.config.response_cache_max_entries,
        )
        self._tools = self._build_tools()
        self._tool_map = {tool.name: tool for tool in self._tools}
        self._resources = self._build_resources()
        self._resource_map = {resource.uri: resource for resource in self._resources}
        self._prompts = self._build_prompts()
        self._prompt_map = {prompt.name: prompt for prompt in self._prompts}
        self.dispatcher = MCPDispatcher(self, self.config)
        self._mounted = False
        self._banner_printed = False
        if not self._attach_start_banner():
            # Fallback for app objects that do not expose a writable `start` attribute.
            self._print_banner_once()

    def _print_banner_once(self) -> None:
        if not self.config.show_banner_on_start or self._banner_printed:
            return
        print(build_install_banner())
        self._banner_printed = True

    def _attach_start_banner(self) -> bool:
        start = getattr(self.app, "start", None)
        if not callable(start):
            return False
        if getattr(start, "__robyn_mcp_banner_wrapped__", False):
            return True

        start_callable: Callable[..., Any] = start

        def _wrapped_start(*args: Any, **kwargs: Any) -> Any:
            self._print_banner_once()
            return start_callable(*args, **kwargs)

        setattr(_wrapped_start, "__robyn_mcp_banner_wrapped__", True)

        try:
            setattr(self.app, "start", _wrapped_start)
        except Exception:
            # Some app objects may not allow runtime attribute assignment.
            return False
        return True

    def _redact_result(self, value: Any) -> Any:
        fields = set(getattr(self.config, "redact_response_fields", set()) or set())
        if not fields:
            return value

        if isinstance(value, dict):
            redacted = {}
            for k, v in value.items():
                if k in fields:
                    redacted[k] = "***REDACTED***"
                else:
                    redacted[k] = self._redact_result(v)
            return redacted

        if isinstance(value, list):
            return [self._redact_result(item) for item in value]

        return value

    @staticmethod
    def _normalize_tag_values(values: list[str] | None) -> list[str]:
        if not values:
            return []
        seen: set[str] = set()
        normalized: list[str] = []
        for value in values:
            token = normalize_tag(value)
            if not token or token in seen:
                continue
            seen.add(token)
            normalized.append(token)
        return normalized

    def _read_cache_tags_for_tool(self, tool: ToolDefinition) -> list[str]:
        tags: list[str] = []
        tags.extend(self._normalize_tag_values(tool.metadata.cache_tags))
        tags.extend(self._normalize_tag_values([f"tool:{tool.name}"]))
        tags.extend(self._normalize_tag_values([f"route:{tool.metadata.path}"]))
        tags.extend(self._normalize_tag_values([f"tag:{tag}" for tag in (tool.metadata.tags or [])]))
        return self._normalize_tag_values(tags)

    def _invalidation_tags_for_tool(self, tool: ToolDefinition) -> list[str]:
        tags: list[str] = []
        tags.extend(self._normalize_tag_values(tool.metadata.invalidate_tags))
        tags.extend(self._normalize_tag_values([f"tag:{tag}" for tag in (tool.metadata.tags or [])]))
        return self._normalize_tag_values(tags)

    def _tool_cache_ttl(self, tool: ToolDefinition) -> int:
        if tool.metadata.cache_ttl_seconds is not None:
            return tool.metadata.cache_ttl_seconds
        return self.config.response_cache_ttl_seconds

    def _should_cache_tool(self, tool: ToolDefinition) -> bool:
        return (
            self.config.enable_response_cache
            and not tool.metadata.side_effect
            and self._tool_cache_ttl(tool) > 0
        )

    def _build_tools(self) -> list[ToolDefinition]:
        filter_engine = FilterEngine(self.config)
        seen: set[str] = set()
        tools: list[ToolDefinition] = []

        for route in extract_routes(self.app, self.config):
            if not filter_engine.allow(route):
                continue

            tool_name = unique_name(slugify_operation(route.operation_id), seen)

            annotations = {
                "idempotentHint": bool(route.idempotent) if route.idempotent is not None else None,
                "authRequired": route.requires_auth,
                "safeReadHint": not route.side_effect,
                "authScopes": route.auth_scopes or None,
                "requiredPermissions": route.required_permissions or None,
                "openWorldSafe": not route.side_effect and not route.requires_auth,
            }

            # NEW: expose source / auto-generation info if present on RouteMetadata
            route_source = getattr(route, "source", None)
            route_auto_generated = getattr(route, "auto_generated", False)
            if route_source:
                annotations["source"] = route_source
            if route_auto_generated:
                annotations["autoGenerated"] = True

            route_cache_ttl = (
                route.cache_ttl_seconds
                if route.cache_ttl_seconds is not None
                else self.config.response_cache_ttl_seconds
            )
            if self.config.enable_response_cache and not route.side_effect and route_cache_ttl > 0:
                annotations["cacheEnabled"] = True
                annotations["cacheTtlSeconds"] = route_cache_ttl
                tags = self._normalize_tag_values(
                    list(route.cache_tags)
                    + [f"tool:{tool_name}", f"route:{route.path}"]
                    + [f"tag:{tag}" for tag in (route.tags or [])]
                )
                if tags:
                    annotations["cacheTags"] = tags
            elif route.side_effect and self.config.enable_response_cache:
                invalidate_tags = self._normalize_tag_values(
                    list(route.invalidate_tags) + [f"tag:{tag}" for tag in (route.tags or [])]
                )
                if invalidate_tags:
                    annotations["invalidateTags"] = invalidate_tags
                elif self.config.response_cache_invalidate_all_on_mutation:
                    annotations["invalidateAllCache"] = True

            tool = ToolDefinition(
                name=tool_name,
                title=route.summary,
                description=build_tool_description(route),
                input_schema=route.request_body_schema or signature_to_input_schema(route.handler),
                metadata=route,
                annotations=annotations,
            )
            tool.annotations = {k: v for k, v in tool.annotations.items() if v is not None}
            tools.append(tool)

        return tools

    def _build_resources(self) -> list[ResourceDefinition]:
        if not self.config.enable_resources:
            return []
        # UPDATED: pass config so auto-exposed resources can be supported
        return extract_resources(self.app, self.config)

    def _build_prompts(self) -> list[PromptDefinition]:
        if not self.config.enable_prompts:
            return []
        return extract_prompts(self.app)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools)

    def list_resources(self) -> list[ResourceDefinition]:
        return list(self._resources)

    def list_prompts(self) -> list[PromptDefinition]:
        return list(self._prompts)

    def compatibility_report(self) -> dict[str, Any]:
        report = build_compatibility_report(self.config)
        report["resourcesEnabled"] = self.config.enable_resources
        report["promptsEnabled"] = self.config.enable_prompts
        report["resourceCount"] = len(self._resources)
        report["promptCount"] = len(self._prompts)

        # NEW: surface feature toggles
        report.setdefault("features", {})
        if isinstance(report["features"], dict):
            report["features"]["playground"] = getattr(self.config, "enable_playground", False)
            report["features"]["openapi_autogen"] = getattr(self.config, "auto_expose_openapi", False)
            report["features"]["tool_tracing"] = getattr(self.config, "enable_tool_tracing", False)
            report["features"]["response_cache"] = getattr(self.config, "enable_response_cache", False)

        return report

    def metrics_snapshot(self) -> dict[str, Any]:
        return self.metrics.snapshot()

    def recent_audit_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.metrics.recent_audit_events(limit=limit)

    def build_request_context(
            self,
            *,
            request: Any,
            session_id: str | None,
            protocol_version: str | None,
    ) -> RequestContext:
        raw_headers = getattr(request, "headers", None)

        def _normalize_headers(raw: Any) -> dict[str, str]:
            if raw is None:
                return {}

            headers: dict[str, str] = {}

            try:
                raw_dict = dict(raw)
            except Exception:
                raw_dict = None

            if raw_dict:
                for k, v in raw_dict.items():
                    try:
                        key = str(k).lower()

                        if isinstance(v, (list, tuple)):
                            if not v:
                                continue
                            value = v[0]
                        else:
                            value = v

                        if isinstance(value, bytes):
                            value = value.decode("utf-8", errors="ignore")
                        else:
                            value = str(value)

                        headers[key] = value
                    except Exception:
                        continue

                if headers:
                    return headers

            for name in (
                    "accept",
                    "content-type",
                    "content-length",
                    "host",
                    "user-agent",
                    "origin",
                    "authorization",
                    "mcp-session-id",
                    "mcp-protocol-version",
                    "cookie",
                    "x-tenant-id",
                    "x-auth-sub",
                    "x-client-id",
                    "x-request-id",
            ):
                try:
                    value = raw.get(name)
                    if value is None:
                        continue

                    if isinstance(value, (list, tuple)):
                        if not value:
                            continue
                        value = value[0]

                    if isinstance(value, bytes):
                        value = value.decode("utf-8", errors="ignore")
                    else:
                        value = str(value)

                    headers[name.lower()] = value
                except Exception:
                    continue

            return headers

        normalized_headers = _normalize_headers(raw_headers)

        forwarded = {
            k: v
            for k, v in normalized_headers.items()
            if k in self.config.forwarded_headers
        }

        cookies: dict[str, str] = {}
        cookie_header = normalized_headers.get("cookie", "")
        if cookie_header and self.config.forwarded_cookies:
            for chunk in cookie_header.split(";"):
                if "=" not in chunk:
                    continue
                key, value = chunk.split("=", 1)
                key = key.strip()
                if key in self.config.forwarded_cookies:
                    cookies[key] = value.strip()

        auth_context = self.principal_resolver.resolve(request, normalized_headers, self.config)

        return RequestContext(
            headers=forwarded,
            cookies=cookies,
            client_id=auth_context.client_id,
            tenant_id=auth_context.tenant_id,
            principal=auth_context.principal,
            principal_id=auth_context.principal_id,
            scopes=auth_context.scopes,
            claims=auth_context.claims,
            session_id=session_id,
            protocol_version=protocol_version,
            origin=normalized_headers.get("origin"),
            raw_request=request,
        )

    def serialize_tool_result(self, result: Any) -> str:
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False, default=str)
        except TypeError:
            return repr(result)

    async def call_tool(
            self,
            name: str,
            arguments: dict[str, Any] | None = None,
            context: RequestContext | None = None,
    ) -> Any:
        arguments = arguments or {}
        context = context or RequestContext()
        tool = self._tool_map.get(name)
        if tool is None:
            for candidate in self._tools:
                if candidate.name == name or candidate.metadata.operation_id == name:
                    tool = candidate
                    break
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")

        cache_key = None
        if self._should_cache_tool(tool):
            cache_key = self.response_cache.build_key(
                tool_name=tool.name,
                arguments=arguments,
                tenant_id=context.tenant_id,
                principal_id=context.principal_id,
                client_id=context.client_id,
                session_id=context.session_id,
                scopes=context.scopes,
            )
            cached = self.response_cache.get(cache_key)
            if cached is not None:
                return self._redact_result(cached)

        result = await self.executor.execute(
            tool_name=name,
            handler=tool.metadata.handler,
            arguments=arguments,
            context=context,
        )
        redacted_result = self._redact_result(result)

        if cache_key is not None:
            self.response_cache.set(
                cache_key,
                redacted_result,
                tags=self._read_cache_tags_for_tool(tool),
                ttl_seconds=self._tool_cache_ttl(tool),
            )

        if self.config.enable_response_cache and tool.metadata.side_effect:
            invalidate_tags = self._invalidation_tags_for_tool(tool)
            if invalidate_tags:
                self.response_cache.invalidate_tags(invalidate_tags)
            elif self.config.response_cache_invalidate_all_on_mutation:
                self.response_cache.clear()

        return redacted_result

    async def read_resource(self, uri: str, context: RequestContext | None = None) -> Any:
        context = context or RequestContext()
        resource = self._resource_map.get(uri)
        if resource is None:
            raise KeyError(f"Unknown resource: {uri}")
        if resource.requires_auth and not context.principal_id:
            raise PermissionError(f"Authentication required for resource: {uri}")
        await self.policy.authorize_resource(uri, context)
        return await self.executor.execute(
            tool_name=f"resource:{uri}",
            handler=resource.handler,
            arguments={},
            context=context,
        )

    async def get_prompt(
            self,
            name: str,
            arguments: dict[str, Any] | None = None,
            context: RequestContext | None = None,
    ) -> Any:
        arguments = arguments or {}
        context = context or RequestContext()
        prompt = self._prompt_map.get(name)
        if prompt is None:
            raise KeyError(f"Unknown prompt: {name}")
        if prompt.requires_auth and not context.principal_id:
            raise PermissionError(f"Authentication required for prompt: {name}")
        await self.policy.authorize_prompt(name, context)
        return await self.executor.execute(
            tool_name=f"prompt:{name}",
            handler=prompt.handler,
            arguments=arguments,
            context=context,
        )

    def mount_http(self, path: str | None = None) -> None:
        if self._mounted:
            return
        mcp_path = path or self.config.mcp_path
        self.config.mcp_path = mcp_path

        @self.app.get(mcp_path)
        async def _mcp_get(request: Any):
            status, headers, body = await self.dispatcher.handle_get(request)
            return self._robyn_response(status, headers, body)

        @self.app.post(mcp_path)
        async def _mcp_post(request: Any):
            try:
                status, headers, body = await self.dispatcher.handle_post(request)
            except ValueError as exc:
                status = 400
                headers = {"content-type": "application/json"}
                body = jsonrpc_error(None, PARSE_ERROR, str(exc) or "Parse error")
            except MCPTransportError as exc:
                status = exc.status_code
                headers = {"content-type": "application/json"}
                body = jsonrpc_error(None, INTERNAL_ERROR, exc.message)
            except Exception as exc:
                status = 500
                headers = {"content-type": "application/json"}
                body = jsonrpc_error(None, INTERNAL_ERROR, str(exc) or "Internal error")
            return self._robyn_response(status, headers, body)

        try:
            @self.app.delete(mcp_path)
            async def _mcp_delete(request: Any):
                status, headers, body = await self.dispatcher.handle_delete(request)
                return self._robyn_response(status, headers, body)
        except Exception:
            pass

        try:
            @self.app.options(mcp_path)
            async def _mcp_options(request: Any):
                status, headers, body = await self.dispatcher.handle_options(request)
                return self._robyn_response(status, headers, body)
        except Exception:
            pass

        # NEW: playground route
        if getattr(self.config, "enable_playground", False):
            playground_path = getattr(self.config, "playground_path", "/mcp/playground")

            @self.app.get(playground_path)
            async def _mcp_playground(request: Any):
                html = build_playground_html(getattr(self.config, "mcp_path", "/mcp"))
                return self._robyn_response(
                    200,
                    {"content-type": "text/html; charset=utf-8"},
                    html,
                )

        self._mounted = True

    def _robyn_response(self, status: int, headers: dict[str, str], body: Any) -> Any:
        try:
            from robyn import Headers, Response

            payload = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
            return Response(
                status_code=status,
                headers=Headers(headers),
                description=payload,
            )
        except Exception:
            return body
