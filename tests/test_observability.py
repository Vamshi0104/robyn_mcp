from __future__ import annotations

from robyn import Robyn

from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool


def test_tool_metrics_record_successful_call():
    app = Robyn(__file__)

    @app.get("/health")
    @expose_tool(summary="Return service health")
    def health():
        return {"ok": True}

    mcp = RobynMCP(
        app,
        config=RobynMCPConfig(
            require_session=False,
            enable_tool_tracing=True,
            trace_include_arguments=True,
            trace_include_result_preview=True,
        ),
    )

    # Use dispatcher path directly to avoid spinning up a server.
    status, headers, body = mcp.dispatcher.handle_jsonrpc_payload(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "health", "arguments": {}},
        },
        headers={},
    )

    assert status == 200
    assert body["result"]["content"]

    snapshot = mcp.metrics.tool_metrics_snapshot()
    assert "health" in snapshot["tools"]
    assert snapshot["tools"]["health"]["count"] >= 1
    assert snapshot["tools"]["health"]["errors"] == 0

    recent = mcp.metrics.recent_tool_events(limit=5)
    assert recent
    assert recent[-1]["toolName"] == "health"
    assert recent[-1]["status"] == "ok"
    assert recent[-1]["durationMs"] >= 0


def test_tool_metrics_record_failed_call():
    app = Robyn(__file__)

    @app.get("/explode")
    @expose_tool(summary="Always fail")
    def explode():
        raise RuntimeError("boom")

    mcp = RobynMCP(
        app,
        config=RobynMCPConfig(
            require_session=False,
            enable_tool_tracing=True,
        ),
    )

    status, headers, body = mcp.dispatcher.handle_jsonrpc_payload(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "explode", "arguments": {}},
        },
        headers={},
    )

    # Depending on your implementation, this may be 200 with MCP error or 500-style JSON-RPC error.
    assert status in {200, 500}
    assert "error" in body or "result" in body

    snapshot = mcp.metrics.tool_metrics_snapshot()
    assert "explode" in snapshot["tools"]
    assert snapshot["tools"]["explode"]["count"] >= 1
    assert snapshot["tools"]["explode"]["errors"] >= 1

    recent = mcp.metrics.recent_tool_events(limit=5)
    assert recent
    assert recent[-1]["toolName"] == "explode"
    assert recent[-1]["status"] == "error"
    assert recent[-1]["errorMessage"] is not None


def test_trace_preview_truncates_large_values():
    app = Robyn(__file__)

    @app.get("/echo")
    @expose_tool(summary="Echo payload")
    def echo(text: str):
        return {"text": text}

    mcp = RobynMCP(
        app,
        config=RobynMCPConfig(
            require_session=False,
            enable_tool_tracing=True,
            trace_include_arguments=True,
            trace_include_result_preview=True,
            trace_max_argument_chars=20,
            trace_max_result_chars=20,
        ),
    )

    long_text = "x" * 200
    status, headers, body = mcp.dispatcher.handle_jsonrpc_payload(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": long_text}},
        },
        headers={},
    )

    assert status == 200

    recent = mcp.metrics.recent_tool_events(limit=5)
    event = recent[-1]
    assert event["toolName"] == "echo"
    assert event["argumentsPreview"] is None or len(event["argumentsPreview"]) <= 20
    assert event["resultPreview"] is None or len(event["resultPreview"]) <= 20