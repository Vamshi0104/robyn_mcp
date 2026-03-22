from __future__ import annotations

from robyn import Robyn

from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool


def test_playground_route_is_mounted_when_enabled():
    app = Robyn(__file__)

    @app.get("/health")
    @expose_tool(summary="Return service health")
    def health():
        return {"ok": True}

    mcp = RobynMCP(
        app,
        config=RobynMCPConfig(
            require_session=False,
            enable_playground=True,
        ),
    )
    mcp.mount_http("/mcp")

    # This checks route presence through Robyn's internal router list.
    routes = getattr(app.router, "routes", [])
    paths = [str(getattr(route, "route", "")) for route in routes]

    assert "/mcp" in paths
    assert "/mcp/playground" in paths


def test_playground_html_contains_mcp_endpoint():
    from robyn_mcp.playground.ui import build_playground_html

    html = build_playground_html("/mcp")

    assert "<html" in html.lower()
    assert "robyn-mcp playground" in html.lower()
    assert "/mcp" in html
    assert "tools/list" in html or "list tools" in html.lower()
    assert "call tool" in html.lower()


def test_playground_custom_path_is_respected():
    app = Robyn(__file__)

    @app.get("/health")
    @expose_tool(summary="Return service health")
    def health():
        return {"ok": True}

    mcp = RobynMCP(
        app,
        config=RobynMCPConfig(
            require_session=False,
            enable_playground=True,
            playground_path="/play",
        ),
    )
    mcp.mount_http("/mcp")

    routes = getattr(app.router, "routes", [])
    paths = [str(getattr(route, "route", "")) for route in routes]

    assert "/play" in paths
    assert "/mcp/playground" not in paths


def test_playground_disabled_does_not_mount_route():
    app = Robyn(__file__)

    @app.get("/health")
    @expose_tool(summary="Return service health")
    def health():
        return {"ok": True}

    mcp = RobynMCP(
        app,
        config=RobynMCPConfig(
            require_session=False,
            enable_playground=False,
        ),
    )
    mcp.mount_http("/mcp")

    routes = getattr(app.router, "routes", [])
    paths = [str(getattr(route, "route", "")) for route in routes]

    assert "/mcp" in paths
    assert "/mcp/playground" not in paths