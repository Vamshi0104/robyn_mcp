from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from robyn_mcp import RobynMCP, RobynMCPConfig, expose_prompt, expose_resource, expose_tool
from robyn_mcp.schemas.json_schema import annotation_to_schema
from robyn_mcp.transport.http import MCPDispatcher


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
    def __init__(self, payload, headers=None) -> None:
        self._payload = payload
        self.headers = headers or {"accept": "application/json"}

    def json(self):
        return self._payload


class NestedPayload(TypedDict):
    city: str
    count: int


@dataclass
class Envelope:
    payload: NestedPayload
    units: Literal["metric", "imperial"] = "metric"


@expose_tool(summary="Weather")
def weather(body: Envelope):
    return {"ok": True}


@expose_resource(uri="config://service/current", name="service-config")
def service_config():
    return {"service": "robyn-mcp", "env": "test"}


@expose_prompt(name="draft-rollout")
def draft_rollout(service: str, audience: str = "internal"):
    return {"messages": [{"role": "user", "content": [{"type": "text", "text": f"Roll out {service} for {audience}"}]}]}


def make_server():
    app = FakeApp(
        [
            FakeRoute("/weather", "POST", weather),
            FakeRoute("/resource", "GET", service_config),
            FakeRoute("/prompt", "GET", draft_rollout),
        ]
    )
    config = RobynMCPConfig(enable_resources=True, enable_prompts=True, require_session=False)
    return RobynMCP(app, config=config)


def test_nested_schema_fidelity():
    schema = annotation_to_schema(Envelope)
    assert schema["type"] == "object"
    assert schema["properties"]["payload"]["type"] == "object"
    assert schema["properties"]["payload"]["properties"]["city"]["type"] == "string"
    assert schema["properties"]["units"]["enum"] == ["metric", "imperial"]


def test_resources_and_prompts_visible_in_initialize_metadata():
    server = make_server()
    dispatcher = MCPDispatcher(server, server.config)
    meta = dispatcher.metadata_document()
    assert "resources" in meta["capabilities"]
    assert "prompts" in meta["capabilities"]


def test_resources_list_and_read():
    server = make_server()
    dispatcher = MCPDispatcher(server, server.config)
    request = DummyRequest({"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}})
    status, _, body = __import__("asyncio").run(dispatcher.handle_post(request))
    assert status == 200
    assert body["result"]["resources"][0]["uri"] == "config://service/current"

    read_request = DummyRequest({"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": "config://service/current"}})
    status, _, body = __import__("asyncio").run(dispatcher.handle_post(read_request))
    assert status == 200
    assert "robyn-mcp" in body["result"]["contents"][0]["text"]


def test_prompts_list_and_get():
    server = make_server()
    dispatcher = MCPDispatcher(server, server.config)
    request = DummyRequest({"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": {}})
    status, _, body = __import__("asyncio").run(dispatcher.handle_post(request))
    assert status == 200
    assert body["result"]["prompts"][0]["name"] == "draft-rollout"

    get_request = DummyRequest(
        {"jsonrpc": "2.0", "id": 2, "method": "prompts/get", "params": {"name": "draft-rollout", "arguments": {"service": "billing"}}}
    )
    status, _, body = __import__("asyncio").run(dispatcher.handle_post(get_request))
    assert status == 200
    assert "billing" in body["result"]["messages"][0]["content"][0]["text"]
