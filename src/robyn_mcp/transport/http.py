from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any

from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.core.models import ToolDefinition
from robyn_mcp.transport.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    jsonrpc_error,
    jsonrpc_result,
)


class MCPTransportError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, code: int = INVALID_REQUEST) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


@dataclass(slots=True)
class MCPSession:
    session_id: str
    protocol_version: str
    client_info: dict[str, Any]
    client_capabilities: dict[str, Any]
    created_at: float
    last_seen_at: float

    def touch(self) -> None:
        self.last_seen_at = time.time()


class SessionStore:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, MCPSession] = {}

    def create(self, *, protocol_version: str, client_info: dict[str, Any], client_capabilities: dict[str, Any]) -> MCPSession:
        session = MCPSession(
            session_id=secrets.token_urlsafe(24),
            protocol_version=protocol_version,
            client_info=client_info,
            client_capabilities=client_capabilities,
            created_at=time.time(),
            last_seen_at=time.time(),
        )
        self._items[session.session_id] = session
        return session

    def get(self, session_id: str | None) -> MCPSession | None:
        self._prune()
        if not session_id:
            return None
        session = self._items.get(session_id)
        if session is not None:
            session.touch()
        return session

    def delete(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        return self._items.pop(session_id, None) is not None

    def _prune(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        stale = [sid for sid, item in self._items.items() if item.last_seen_at < cutoff]
        for sid in stale:
            self._items.pop(sid, None)


class HTTPContextAdapter:
    def __init__(self, config: RobynMCPConfig) -> None:
        self.config = config

    def extract_headers(self, request) -> dict[str, str]:
        raw_headers = getattr(request, "headers", None)
        if raw_headers is None:
            return {}

        headers: dict[str, str] = {}

        try:
            raw_dict = dict(raw_headers)
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

        for name in [
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
        ]:
            try:
                value = raw_headers.get(name)
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

    def validate_origin(self, headers: dict[str, str]) -> None:
        origin = headers.get("origin")
        if origin is None and self.config.allow_no_origin:
            return
        if origin is None:
            raise MCPTransportError("Origin header is required", status_code=403)
        if self.config.allowed_origins is None:
            return
        if origin not in self.config.allowed_origins:
            raise MCPTransportError("Origin not allowed", status_code=403)

    def validate_accept(self, headers: dict[str, str]) -> None:
        if not self.config.require_accept_header:
            return
        accept = headers.get("accept", "")
        if "application/json" not in accept and "text/event-stream" not in accept and "*/*" not in accept:
            raise MCPTransportError(
                "Accept header must include application/json or text/event-stream",
                status_code=406,
            )

    def negotiate_protocol_version(self, headers: dict[str, str]) -> str:
        version = headers.get("mcp-protocol-version")
        if not version:
            return self.config.protocol_version
        if version not in {"2025-03-26", "2025-06-18", self.config.protocol_version}:
            raise MCPTransportError("Unsupported MCP protocol version", status_code=400)
        return version


class MCPDispatcher:
    def __init__(self, server: Any, config: RobynMCPConfig) -> None:
        self.server = server
        self.config = config
        self.sessions = SessionStore(ttl_seconds=config.session_ttl_seconds)
        self.adapter = HTTPContextAdapter(config)

    def build_tools_list_result(self) -> dict[str, Any]:
        tools, next_cursor = self._paginate_tools(None)
        result: dict[str, Any] = {"tools": tools}
        if next_cursor is not None:
            result["nextCursor"] = next_cursor
        return result

    def handle_jsonrpc_payload(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], dict[str, Any]]:
        """
        Backward-compatible synchronous helper used by tests.
        """
        headers = headers or {}

        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}

        if payload.get("jsonrpc") != "2.0" or not isinstance(method, str):
            return 400, {"content-type": "application/json"}, jsonrpc_error(
                request_id, INVALID_REQUEST, "Invalid JSON-RPC request"
            )

        if method == "tools/list":
            return 200, {"content-type": "application/json"}, jsonrpc_result(
                request_id, self.build_tools_list_result()
            )

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}

            if not isinstance(name, str):
                return 400, {"content-type": "application/json"}, jsonrpc_error(
                    request_id, INVALID_PARAMS, "tools/call requires a string 'name'"
                )
            if not isinstance(arguments, dict):
                return 400, {"content-type": "application/json"}, jsonrpc_error(
                    request_id, INVALID_PARAMS, "tools/call requires object 'arguments'"
                )

            import asyncio

            context = self.server.build_request_context(
                request=None,
                session_id=headers.get("mcp-session-id"),
                protocol_version=headers.get("mcp-protocol-version") or self.config.protocol_version,
            )

            try:
                result = asyncio.run(
                    self.server.call_tool(name=name, arguments=arguments, context=context)
                )
            except KeyError:
                return 404, {"content-type": "application/json"}, jsonrpc_error(
                    request_id, METHOD_NOT_FOUND, f"Unknown tool: {name}"
                )
            except PermissionError as exc:
                return 403, {"content-type": "application/json"}, jsonrpc_error(
                    request_id, INVALID_PARAMS, str(exc)
                )
            except Exception as exc:
                return 500, {"content-type": "application/json"}, jsonrpc_error(
                    request_id, INTERNAL_ERROR, str(exc)
                )

            content = result if isinstance(result, list) else [{"type": "text", "text": self.server.serialize_tool_result(result)}]
            return 200, {"content-type": "application/json"}, jsonrpc_result(
                request_id, {"content": content}
            )

        return 404, {"content-type": "application/json"}, jsonrpc_error(
            request_id, METHOD_NOT_FOUND, f"Unknown method: {method}"
        )

    def metadata_document(self) -> dict[str, Any]:
        capabilities: dict[str, Any] = {"tools": {"listChanged": False}}
        if self.config.enable_resources:
            capabilities["resources"] = {"listChanged": False, "subscribe": False}
        if self.config.enable_prompts:
            capabilities["prompts"] = {"listChanged": False}

        payload = {
            "name": self.config.name,
            "version": self.config.version,
            "protocolVersion": self.config.protocol_version,
            "endpoint": self.config.mcp_path,
            "capabilities": capabilities,
            "legacySseEnabled": self.config.enable_legacy_sse,
            "compatibility": self.server.compatibility_report(),
            "metrics": self.server.metrics_snapshot() if self.config.enable_metrics else None,
        }

        # NEW: richer observability surfaced in metadata
        if hasattr(self.server, "metrics"):
            tool_metrics_fn = getattr(self.server.metrics, "tool_metrics_snapshot", None)
            recent_tool_events_fn = getattr(self.server.metrics, "recent_tool_events", None)
            if callable(tool_metrics_fn):
                payload["toolMetrics"] = tool_metrics_fn()
            if callable(recent_tool_events_fn):
                payload["recentToolEvents"] = recent_tool_events_fn(limit=20)

        if self.config.enable_audit_log:
            payload["recentAuditEvents"] = self.server.recent_audit_events(limit=20)

        return payload

    def build_initialize_result(self) -> dict[str, Any]:
        capabilities: dict[str, Any] = {"tools": {"listChanged": False}}
        if self.config.enable_resources:
            capabilities["resources"] = {"listChanged": False, "subscribe": False}
        if self.config.enable_prompts:
            capabilities["prompts"] = {"listChanged": False}
        result: dict[str, Any] = {
            "protocolVersion": self.config.protocol_version,
            "capabilities": capabilities,
            "serverInfo": {
                "name": self.config.name,
                "version": self.config.version,
            },
        }
        if self.config.include_server_instructions and self.config.instructions:
            result["instructions"] = self.config.instructions
        return result

    def _serialize_tool(self, tool: ToolDefinition) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema,
        }
        if tool.title:
            payload["title"] = tool.title
        if tool.annotations:
            payload["annotations"] = tool.annotations
        if tool.metadata.side_effect is False:
            payload.setdefault("annotations", {})["readOnlyHint"] = True
        if getattr(tool.metadata, "response_schema", None):
            payload["outputSchema"] = tool.metadata.response_schema
        if getattr(tool.metadata, "examples", None) and self.config.publish_examples_in_tool_description:
            payload["examples"] = tool.metadata.examples[:3]
        return payload

    def _serialize_resource(self, resource: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "uri": resource.uri,
            "name": resource.name,
            "mimeType": resource.mime_type,
        }
        if resource.description:
            payload["description"] = resource.description
        if resource.annotations:
            payload["annotations"] = resource.annotations
        return payload

    def _serialize_prompt(self, prompt: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": prompt.name,
            "arguments": [
                {
                    "name": arg.name,
                    "required": arg.required,
                    **({"description": arg.description} if arg.description else {}),
                }
                for arg in prompt.arguments
            ],
        }
        if prompt.title:
            payload["title"] = prompt.title
        if prompt.description:
            payload["description"] = prompt.description
        if prompt.annotations:
            payload["annotations"] = prompt.annotations
        return payload

    def _paginate_tools(self, cursor: str | None) -> tuple[list[dict[str, Any]], str | None]:
        tools = [self._serialize_tool(tool) for tool in self.server.list_tools()]
        start = int(cursor) if cursor else 0
        end = min(start + self.config.max_tools_per_page, len(tools))
        next_cursor = str(end) if end < len(tools) else None
        return tools[start:end], next_cursor

    async def handle_get(self, request: Any) -> tuple[int, dict[str, str], dict[str, Any]]:
        headers = self.adapter.extract_headers(request)
        self.adapter.validate_origin(headers)
        accept = headers.get("accept", "application/json")
        if "text/event-stream" in accept and not self.config.enable_legacy_sse:
            raise MCPTransportError("SSE is disabled; use HTTP POST/GET JSON transport", status_code=406)

        payload = self.metadata_document()
        return 200, {"content-type": "application/json"}, payload

    async def handle_post(self, request: Any) -> tuple[int, dict[str, str], dict[str, Any]]:
        headers = self.adapter.extract_headers(request)
        self.adapter.validate_origin(headers)
        self.adapter.validate_accept(headers)
        header_version = self.adapter.negotiate_protocol_version(headers)

        payload = request.json() if hasattr(request, "json") else None
        if not isinstance(payload, dict):
            raise MCPTransportError("Request body must be a JSON-RPC object", status_code=400)

        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}
        if payload.get("jsonrpc") != "2.0" or not isinstance(method, str):
            return 400, {"content-type": "application/json"}, jsonrpc_error(
                request_id, INVALID_REQUEST, "Invalid JSON-RPC request"
            )

        if method == "initialize":
            client_info = params.get("clientInfo") or {}
            client_capabilities = params.get("capabilities") or {}
            session = self.sessions.create(
                protocol_version=self.config.protocol_version,
                client_info=client_info,
                client_capabilities=client_capabilities,
            )
            response_headers = {
                "content-type": "application/json",
                "mcp-session-id": session.session_id,
                "mcp-protocol-version": self.config.protocol_version,
            }
            return 200, response_headers, jsonrpc_result(request_id, self.build_initialize_result())

        session = self.sessions.get(headers.get("mcp-session-id"))
        if self.config.require_session and session is None:
            raise MCPTransportError("Missing or expired MCP session", status_code=400)

        if method == "notifications/initialized":
            return 202, {"content-type": "application/json"}, {}

        if method == "ping":
            return 200, {"content-type": "application/json"}, jsonrpc_result(request_id, {})

        if method == "robyn_mcp/compatibility":
            return 200, {"content-type": "application/json"}, jsonrpc_result(request_id, self.server.compatibility_report())

        if method == "robyn_mcp/metrics":
            result_payload = {
                "metrics": self.server.metrics_snapshot(),
                "recentAuditEvents": self.server.recent_audit_events(limit=50),
            }
            if hasattr(self.server, "metrics"):
                tool_metrics_fn = getattr(self.server.metrics, "tool_metrics_snapshot", None)
                recent_tool_events_fn = getattr(self.server.metrics, "recent_tool_events", None)
                if callable(tool_metrics_fn):
                    result_payload["toolMetrics"] = tool_metrics_fn()
                if callable(recent_tool_events_fn):
                    result_payload["recentToolEvents"] = recent_tool_events_fn(limit=50)

            return 200, {"content-type": "application/json"}, jsonrpc_result(
                request_id,
                result_payload,
            )

        if method == "tools/list":
            cursor = params.get("cursor")
            tools, next_cursor = self._paginate_tools(cursor)
            result: dict[str, Any] = {"tools": tools}
            if next_cursor is not None:
                result["nextCursor"] = next_cursor
            return 200, {"content-type": "application/json", "mcp-protocol-version": header_version}, jsonrpc_result(request_id, result)

        if method == "resources/list":
            resources = [self._serialize_resource(resource) for resource in self.server.list_resources()]
            return 200, {"content-type": "application/json", "mcp-protocol-version": header_version}, jsonrpc_result(
                request_id,
                {"resources": resources},
            )

        if method == "resources/read":
            uri = params.get("uri")
            if not isinstance(uri, str):
                return 400, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    INVALID_PARAMS,
                    "resources/read requires a string 'uri'",
                )
            context = self.server.build_request_context(
                request=request,
                session_id=session.session_id if session else None,
                protocol_version=header_version,
            )
            try:
                result = await self.server.read_resource(uri=uri, context=context)
            except KeyError:
                return 404, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    METHOD_NOT_FOUND,
                    f"Unknown resource: {uri}",
                )
            except PermissionError as exc:
                return 403, {"content-type": "application/json"}, jsonrpc_error(request_id, INVALID_PARAMS, str(exc))
            text_value = self.server.serialize_tool_result(result)
            resource = self.server._resource_map[uri]
            return 200, {"content-type": "application/json", "mcp-protocol-version": header_version}, jsonrpc_result(
                request_id,
                {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": resource.mime_type,
                            "text": text_value,
                        }
                    ]
                },
            )

        if method == "prompts/list":
            prompts = [self._serialize_prompt(prompt) for prompt in self.server.list_prompts()]
            return 200, {"content-type": "application/json", "mcp-protocol-version": header_version}, jsonrpc_result(
                request_id,
                {"prompts": prompts},
            )

        if method == "prompts/get":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(name, str):
                return 400, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    INVALID_PARAMS,
                    "prompts/get requires a string 'name'",
                )
            if not isinstance(arguments, dict):
                return 400, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    INVALID_PARAMS,
                    "prompts/get requires object 'arguments'",
                )
            context = self.server.build_request_context(
                request=request,
                session_id=session.session_id if session else None,
                protocol_version=header_version,
            )
            try:
                prompt_result = await self.server.get_prompt(name=name, arguments=arguments, context=context)
            except KeyError:
                return 404, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    METHOD_NOT_FOUND,
                    f"Unknown prompt: {name}",
                )
            except PermissionError as exc:
                return 403, {"content-type": "application/json"}, jsonrpc_error(request_id, INVALID_PARAMS, str(exc))
            if isinstance(prompt_result, dict) and "messages" in prompt_result:
                result_payload = prompt_result
            else:
                result_payload = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": self.server.serialize_tool_result(prompt_result)}],
                        }
                    ]
                }
            return 200, {"content-type": "application/json", "mcp-protocol-version": header_version}, jsonrpc_result(
                request_id,
                result_payload,
            )

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(name, str):
                return 400, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    INVALID_PARAMS,
                    "tools/call requires a string 'name'",
                )
            if not isinstance(arguments, dict):
                return 400, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    INVALID_PARAMS,
                    "tools/call requires object 'arguments'",
                )
            context = self.server.build_request_context(
                request=request,
                session_id=session.session_id if session else None,
                protocol_version=header_version,
            )
            try:
                result = await self.server.call_tool(name=name, arguments=arguments, context=context)
            except KeyError:
                return 404, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    METHOD_NOT_FOUND,
                    f"Unknown tool: {name}",
                )
            except PermissionError as exc:
                return 403, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    INVALID_PARAMS,
                    str(exc),
                )
            except Exception as exc:  # pragma: no cover - final fallback
                return 500, {"content-type": "application/json"}, jsonrpc_error(
                    request_id,
                    INTERNAL_ERROR,
                    str(exc),
                )
            content = result if isinstance(result, list) else [{"type": "text", "text": self.server.serialize_tool_result(result)}]
            return 200, {"content-type": "application/json", "mcp-protocol-version": header_version}, jsonrpc_result(
                request_id,
                {"content": content},
            )

        return 404, {"content-type": "application/json"}, jsonrpc_error(request_id, METHOD_NOT_FOUND, f"Unknown method: {method}")

    async def handle_delete(self, request: Any) -> tuple[int, dict[str, str], dict[str, Any]]:
        headers = self.adapter.extract_headers(request)
        self.adapter.validate_origin(headers)
        session_id = headers.get("mcp-session-id")
        removed = self.sessions.delete(session_id)
        if not removed:
            return 404, {"content-type": "application/json"}, {"ok": False, "message": "Session not found"}
        return 200, {"content-type": "application/json"}, {"ok": True}

    async def handle_options(self, request: Any) -> tuple[int, dict[str, str], dict[str, Any]]:
        return 204, {
            "allow": "GET, POST, DELETE, OPTIONS",
            "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
            "access-control-allow-headers": "content-type, accept, mcp-session-id, mcp-protocol-version, authorization",
        }, {}