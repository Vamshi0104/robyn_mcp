from __future__ import annotations

import asyncio
import io
import json
import urllib.error
import urllib.request

from robyn_mcp.adapters.fastapi import FastAPIOperationSource
from robyn_mcp.core.models import RequestContext
from robyn_mcp.core.openapi_gateway import OpenAPIGatewayConfig, OpenAPIGatewayInvoker
from robyn_mcp.core.openapi_source import OpenAPIOperationSource
from robyn_mcp.testing.openapi_benchmark import benchmark_openapi_inspection


class _FakeResponse:
    status = 200
    headers = {"content-type": "application/json"}

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def _spec():
    return {
        "openapi": "3.1.0",
        "info": {"title": "Gateway API", "version": "1.0.0"},
        "paths": {
            "/customers/{customer_id}": {
                "get": {
                    "operationId": "getCustomer",
                    "description": "Read a customer profile for support workflows.",
                    "parameters": [
                        {
                            "name": "customer_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"name": "expand", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
                "patch": {
                    "operationId": "updateCustomer",
                    "description": "Update customer profile fields after validation.",
                    "parameters": [
                        {
                            "name": "customer_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"status": {"type": "string"}},
                                    "required": ["status"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "OK"}},
                },
            }
        },
    }


def test_openapi_gateway_invokes_get_with_path_and_query(monkeypatch):
    operation = {item.name: item for item in OpenAPIOperationSource(_spec()).discover()}[
        "get_customer"
    ]
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["headers"] = dict(request.header_items())
        return _FakeResponse({"ok": True})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = asyncio.run(
        OpenAPIGatewayInvoker(OpenAPIGatewayConfig("https://api.example.test")).invoke(
            operation,
            {"customer_id": "cus 1", "expand": "orders"},
            RequestContext(headers={"authorization": "Bearer abc", "cookie": "nope"}),
        )
    )

    assert result.status_code == 200
    assert seen["method"] == "GET"
    assert seen["url"] == "https://api.example.test/customers/cus%201?expand=orders"
    assert seen["headers"]["Authorization"] == "Bearer abc"
    assert "Cookie" not in seen["headers"]


def test_openapi_gateway_invokes_patch_with_json_body(monkeypatch):
    operation = {item.name: item for item in OpenAPIOperationSource(_spec()).discover()}[
        "update_customer"
    ]
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["data"] = json.loads(request.data.decode())
        return _FakeResponse({"updated": True})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = asyncio.run(
        OpenAPIGatewayInvoker(OpenAPIGatewayConfig("https://api.example.test")).invoke(
            operation,
            {"customer_id": "cus-1", "status": "active"},
            RequestContext(),
        )
    )

    assert result.value == {"updated": True}
    assert seen["method"] == "PATCH"
    assert seen["url"] == "https://api.example.test/customers/cus-1"
    assert seen["data"] == {"status": "active"}


def test_openapi_gateway_returns_http_error_payload(monkeypatch):
    operation = {item.name: item for item in OpenAPIOperationSource(_spec()).discover()}[
        "update_customer"
    ]

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            409,
            "Conflict",
            {"content-type": "application/json"},
            io.BytesIO(b'{"error":"conflict"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = asyncio.run(
        OpenAPIGatewayInvoker(OpenAPIGatewayConfig("https://api.example.test")).invoke(
            operation,
            {"customer_id": "cus-1", "status": "active"},
            RequestContext(),
        )
    )

    assert result.status_code == 409
    assert result.value == {"error": "conflict"}
    assert result.metadata["error"] is True


def test_openapi_gateway_returns_network_error(monkeypatch):
    operation = {item.name: item for item in OpenAPIOperationSource(_spec()).discover()}[
        "get_customer"
    ]

    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = asyncio.run(
        OpenAPIGatewayInvoker(OpenAPIGatewayConfig("https://api.example.test")).invoke(
            operation,
            {"customer_id": "cus-1"},
            RequestContext(),
        )
    )

    assert result.status_code is None
    assert result.value == {"error": "offline"}
    assert result.metadata["error"] is True


def test_openapi_gateway_rejects_missing_path_argument(monkeypatch):
    operation = {item.name: item for item in OpenAPIOperationSource(_spec()).discover()}[
        "get_customer"
    ]

    def fake_urlopen(request, timeout):  # pragma: no cover - should not be called
        raise AssertionError("missing path arguments should fail before request")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    try:
        asyncio.run(
            OpenAPIGatewayInvoker(OpenAPIGatewayConfig("https://api.example.test")).invoke(
                operation,
                {"expand": "orders"},
                RequestContext(),
            )
        )
    except ValueError as exc:
        assert "customer_id" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_openapi_source_keeps_path_parameter_when_body_field_collides():
    spec = _spec()
    body_schema = spec["paths"]["/customers/{customer_id}"]["patch"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    body_schema["properties"]["customer_id"] = {"type": "string"}
    body_schema["required"].append("customer_id")

    operation = {item.name: item for item in OpenAPIOperationSource(spec).discover()}[
        "update_customer"
    ]

    assert operation.input_schema["properties"]["customer_id"]["x-mcp-source"] == "path"
    assert operation.input_schema["properties"]["status"]["x-mcp-source"] == "body"


def test_fastapi_operation_source_uses_openapi_document():
    class FakeFastAPI:
        def openapi(self):
            return _spec()

    operations = FastAPIOperationSource(FakeFastAPI()).discover()
    assert {operation.name for operation in operations} == {"get_customer", "update_customer"}


def test_benchmark_openapi_inspection(tmp_path):
    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(_spec()))
    payload = benchmark_openapi_inspection(path, iterations=3)
    assert payload["iterations"] == 3
    assert payload["operationCount"] == 2
    assert payload["meanMs"] >= 0
