from __future__ import annotations

from dataclasses import dataclass

import pytest

from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.core.server import RobynMCP
from robyn_mcp.transport.http import SessionStore


@dataclass
class DummyRequest:
    payload: dict
    headers: dict[str, str]
    identity: dict | None = None

    def json(self):
        return self.payload


class Route:
    def __init__(self, method: str, path: str, handler):
        self.route_type = method
        self.route = path
        self.handler = handler


class DummyApp:
    def __init__(self) -> None:
        self.routes = [Route("GET", "/sum", sum_values)]

    def get(self, path):
        def decorator(fn):
            return fn
        return decorator

    def post(self, path):
        def decorator(fn):
            return fn
        return decorator


def sum_values(a: int, b: int) -> dict[str, int]:
    return {"sum": a + b}


@pytest.mark.asyncio
async def test_initialize_then_list_and_call() -> None:
    app = DummyApp()
    server = RobynMCP(app, config=RobynMCPConfig(allow_no_origin=True))

    init_request = DummyRequest(
        payload={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"clientInfo": {"name": "test-client"}, "capabilities": {}},
        },
        headers={"accept": "application/json, text/event-stream"},
    )
    status, headers, body = await server.dispatcher.handle_post(init_request)
    assert status == 200
    session_id = headers["mcp-session-id"]
    assert body["result"]["serverInfo"]["name"] == "robyn-mcp"

    list_request = DummyRequest(
        payload={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        headers={
            "accept": "application/json, text/event-stream",
            "mcp-session-id": session_id,
            "mcp-protocol-version": "2025-11-25",
        },
    )
    status, _, body = await server.dispatcher.handle_post(list_request)
    assert status == 200
    assert body["result"]["tools"][0]["name"] == "sum_values"

    call_request = DummyRequest(
        payload={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "sum_values", "arguments": {"a": 2, "b": 5}},
        },
        headers={
            "accept": "application/json, text/event-stream",
            "mcp-session-id": session_id,
            "mcp-protocol-version": "2025-11-25",
        },
    )
    status, _, body = await server.dispatcher.handle_post(call_request)
    assert status == 200
    assert '"sum": 7' in body["result"]["content"][0]["text"]


def test_session_store_prunes_expired_entries() -> None:
    store = SessionStore(ttl_seconds=1)
    session = store.create(protocol_version="2025-11-25", client_info={}, client_capabilities={})
    assert store.get(session.session_id) is not None
