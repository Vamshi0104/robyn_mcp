from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from robyn_mcp.core.models import RequestContext
from robyn_mcp.core.operations import InvocationResult, Operation


@dataclass(slots=True)
class OpenAPIGatewayConfig:
    upstream_base_url: str
    timeout_seconds: float = 10.0
    allowed_forward_headers: set[str] = field(
        default_factory=lambda: {"authorization", "x-request-id", "x-tenant-id"}
    )
    static_headers: dict[str, str] = field(default_factory=dict)


class OpenAPIGatewayInvoker:
    def __init__(self, config: OpenAPIGatewayConfig) -> None:
        self.config = config

    def _split_arguments(
        self, operation: Operation, arguments: dict[str, Any]
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        path = operation.path
        query: dict[str, Any] = {}
        body: dict[str, Any] = {}
        properties = operation.input_schema.get("properties") or {}

        for key, value in arguments.items():
            source = (
                properties.get(key, {}).get("x-mcp-source")
                if isinstance(properties.get(key), dict)
                else None
            )
            if source == "path":
                path = path.replace("{" + key + "}", urllib.parse.quote(str(value), safe=""))
            elif source == "query" or operation.method.upper() in {
                "GET",
                "DELETE",
                "HEAD",
                "OPTIONS",
            }:
                query[key] = value
            else:
                body[key] = value

        unresolved = sorted(set(part for part in path.split("{")[1:] if "}" in part))
        if unresolved:
            names = ", ".join(item.split("}", 1)[0] for item in unresolved)
            raise ValueError(f"Missing required path argument(s): {names}")

        return path, query, body

    def _build_url(self, path: str, query: dict[str, Any]) -> str:
        base = self.config.upstream_base_url.rstrip("/") + "/"
        url = urllib.parse.urljoin(base, path.lstrip("/"))
        if query:
            encoded = urllib.parse.urlencode(
                {key: value for key, value in query.items() if value is not None},
                doseq=True,
            )
            if encoded:
                separator = "&" if "?" in url else "?"
                url = url + separator + encoded
        return url

    def _headers(self, context: RequestContext) -> dict[str, str]:
        headers = {str(k).lower(): str(v) for k, v in self.config.static_headers.items()}
        allowed = {item.lower() for item in self.config.allowed_forward_headers}
        for key, value in (context.headers or {}).items():
            key_l = str(key).lower()
            if key_l in allowed:
                headers[key_l] = str(value)
        return headers

    async def invoke(
        self,
        operation: Operation,
        arguments: dict[str, Any],
        context: RequestContext,
    ) -> InvocationResult:
        path, query, body = self._split_arguments(operation, arguments)
        url = self._build_url(path, query)
        data = None
        headers = self._headers(context)
        if body:
            data = json.dumps(body).encode("utf-8")
            headers.setdefault("content-type", "application/json")
        headers.setdefault("accept", "application/json")

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=operation.method.upper(),
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                value: Any
                try:
                    value = json.loads(raw) if raw else None
                except json.JSONDecodeError:
                    value = raw
                return InvocationResult(
                    value=value,
                    status_code=response.status,
                    headers={key.lower(): value for key, value in response.headers.items()},
                    metadata={"url": url, "method": operation.method.upper()},
                )
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                value = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                value = raw
            return InvocationResult(
                value=value,
                status_code=exc.code,
                headers={key.lower(): value for key, value in exc.headers.items()},
                metadata={"url": url, "method": operation.method.upper(), "error": True},
            )
        except urllib.error.URLError as exc:
            return InvocationResult(
                value={"error": str(exc.reason)},
                status_code=None,
                headers={},
                metadata={"url": url, "method": operation.method.upper(), "error": True},
            )


def find_operation(operations: list[Operation], name: str) -> Operation:
    for operation in operations:
        if operation.name == name or operation.metadata.get("operation_id") == name:
            return operation
    raise KeyError(f"Unknown OpenAPI operation: {name}")
