from __future__ import annotations

import asyncio

from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool
from robyn_mcp.security.policy import RequestContext


class FakeRoute:
    def __init__(self, path: str, method: str, handler, auth_required: bool = False) -> None:
        self.route = path
        self.route_type = method
        self.handler = handler
        self.auth_required = auth_required


class FakeApp:
    def __init__(self, routes) -> None:
        self.routes = routes


def test_response_cache_reuses_read_result_for_same_context_and_args():
    calls = {"count": 0}

    @expose_tool(operation_id="list_inventory", side_effect=False, cache_tags=["inventory"])
    def list_inventory(region: str):
        calls["count"] += 1
        return {"region": region, "version": calls["count"]}

    app = FakeApp([FakeRoute("/inventory", "GET", list_inventory)])
    server = RobynMCP(
        app,
        config=RobynMCPConfig(
            require_session=False,
            enable_response_cache=True,
            response_cache_ttl_seconds=120,
        ),
    )
    ctx = RequestContext(tenant_id="acme", principal_id="user-1")

    first = asyncio.run(server.call_tool("list_inventory", {"region": "us"}, context=ctx))
    second = asyncio.run(server.call_tool("list_inventory", {"region": "us"}, context=ctx))

    assert first == second
    assert calls["count"] == 1


def test_response_cache_isolated_by_principal_context():
    calls = {"count": 0}

    @expose_tool(operation_id="list_orders", side_effect=False, cache_tags=["orders"])
    def list_orders():
        calls["count"] += 1
        return {"version": calls["count"]}

    app = FakeApp([FakeRoute("/orders", "GET", list_orders)])
    server = RobynMCP(
        app,
        config=RobynMCPConfig(require_session=False, enable_response_cache=True),
    )

    result_a = asyncio.run(
        server.call_tool("list_orders", {}, context=RequestContext(tenant_id="acme", principal_id="user-a"))
    )
    result_b = asyncio.run(
        server.call_tool("list_orders", {}, context=RequestContext(tenant_id="acme", principal_id="user-b"))
    )

    assert result_a != result_b
    assert calls["count"] == 2


def test_mutation_invalidates_cache_by_tags():
    calls = {"list": 0, "write": 0}

    @expose_tool(operation_id="list_users", side_effect=False, cache_tags=["users"])
    def list_users():
        calls["list"] += 1
        return {"version": calls["list"]}

    @expose_tool(operation_id="upsert_user", side_effect=True, invalidate_tags=["users"])
    def upsert_user(name: str):
        calls["write"] += 1
        return {"ok": True, "name": name}

    app = FakeApp(
        [
            FakeRoute("/users", "GET", list_users),
            FakeRoute("/users", "POST", upsert_user),
        ]
    )
    server = RobynMCP(
        app,
        config=RobynMCPConfig(require_session=False, enable_response_cache=True),
    )

    first = asyncio.run(server.call_tool("list_users", {}))
    second = asyncio.run(server.call_tool("list_users", {}))
    asyncio.run(server.call_tool("upsert_user", {"name": "Ada"}))
    third = asyncio.run(server.call_tool("list_users", {}))

    assert first == second
    assert first != third
    assert calls["list"] == 2
    assert calls["write"] == 1


def test_mutation_without_tags_clears_cache_by_default():
    calls = {"list": 0, "write": 0}

    @expose_tool(operation_id="fetch_products", side_effect=False, cache_tags=["products"])
    def fetch_products():
        calls["list"] += 1
        return {"version": calls["list"]}

    @expose_tool(operation_id="rebuild_catalog", side_effect=True)
    def rebuild_catalog():
        calls["write"] += 1
        return {"ok": True}

    app = FakeApp(
        [
            FakeRoute("/products", "GET", fetch_products),
            FakeRoute("/catalog/rebuild", "POST", rebuild_catalog),
        ]
    )
    server = RobynMCP(
        app,
        config=RobynMCPConfig(
            require_session=False,
            enable_response_cache=True,
            response_cache_invalidate_all_on_mutation=True,
        ),
    )

    first = asyncio.run(server.call_tool("fetch_products", {}))
    second = asyncio.run(server.call_tool("fetch_products", {}))
    asyncio.run(server.call_tool("rebuild_catalog", {}))
    third = asyncio.run(server.call_tool("fetch_products", {}))

    assert first == second
    assert first != third
    assert calls["list"] == 2
    assert calls["write"] == 1
