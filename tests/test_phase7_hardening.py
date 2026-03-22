
from __future__ import annotations

import asyncio

from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool
from robyn_mcp.transport.http import MCPDispatcher, MCPTransportError


class FakeRoute:
    def __init__(self, path: str, method: str, handler, auth_required: bool = False) -> None:
        self.route = path
        self.route_type = method
        self.handler = handler
        self.auth_required = auth_required


class FakeApp:
    def __init__(self, routes):
        self.routes = routes


class DummyRequest:
    def __init__(self, payload=None, headers=None) -> None:
        self._payload = payload
        self.headers = headers or {"accept": "application/json"}

    def json(self):
        return self._payload


@expose_tool(
    summary="Get customer profile",
    human_summary="Read the customer profile for the supplied id.",
    requires_auth=True,
    auth_scopes=["customer.read"],
    required_permissions=["customer:read"],
    side_effect=False,
    idempotent=True,
    examples=[{"name": "lookup", "arguments": {"customer_id": "cus_123"}}],
)
def customer_profile(customer_id: str):
    return {"customer_id": customer_id, "secret_token": "abc", "nested": {"secret_token": "def"}}


def make_server():
    app = FakeApp([FakeRoute("/customers/{customer_id}", "GET", customer_profile, auth_required=True)])
    config = RobynMCPConfig(require_session=False, redact_response_fields={"secret_token"})
    return RobynMCP(app, config=config)


def test_phase7_description_and_examples():
    server = make_server()
    tool = server.list_tools()[0]
    assert "Permissions required: customer:read." in tool.description
    assert "Retry behavior: idempotent." in tool.description
    assert "Examples available: lookup." in tool.description
    assert tool.annotations["requiredPermissions"] == ["customer:read"]


def test_phase7_redaction_for_tool_output():
    server = make_server()
    result = asyncio.run(server.call_tool("customer_profile", {"customer_id": "cus_123"}))
    assert result["secret_token"] == "***REDACTED***"
    assert result["nested"]["secret_token"] == "***REDACTED***"


def test_phase7_sse_disabled_by_default():
    server = make_server()
    dispatcher = MCPDispatcher(server, server.config)
    request = DummyRequest(headers={"accept": "text/event-stream"})
    try:
        asyncio.run(dispatcher.handle_get(request))
        assert False, "expected MCPTransportError"
    except MCPTransportError as exc:
        assert exc.status_code == 406


def test_phase7_compatibility_runtime_status():
    server = make_server()
    report = server.compatibility_report()
    assert "runtime_status" in report
    assert report["runtime_status"]["validation_mode"] in {"live", "contract-only"}
