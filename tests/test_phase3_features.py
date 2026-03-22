from robyn_mcp.core.compat import build_compatibility_report
from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.observability.metrics import MetricsCollector
from robyn_mcp.security.policy import PolicyEngine, RequestContext, ScopedPolicyEngine


async def _authorize(engine, tool_name, context):
    await engine.authorize_tool(tool_name, context)


def test_compatibility_report_shape():
    report = build_compatibility_report(RobynMCPConfig())
    assert report["transports"]["http"] is True
    assert report["features"]["tools"] is True


def test_metrics_snapshot_updates():
    collector = MetricsCollector()
    context = RequestContext(principal_id="user-1", session_id="s1")
    collector.record_success("get_user", 12.5, context)
    collector.record_error("get_user", 8.0, context, "ValueError")
    snapshot = collector.snapshot()
    assert snapshot["get_user"]["calls"] == 2
    assert snapshot["get_user"]["errors"] == 1


def test_rate_limit_policy_blocks_after_capacity():
    engine = PolicyEngine(
        config=RobynMCPConfig(
            rate_limit_enabled=True,
            rate_limit_capacity=1,
            rate_limit_refill_per_second=1000,
        )
    )
    ctx = RequestContext(session_id="s1")
    import asyncio

    asyncio.run(_authorize(engine, "tool_a", ctx))
    try:
        asyncio.run(_authorize(engine, "tool_a", ctx))
        assert False, "expected PermissionError"
    except PermissionError:
        assert True


def test_scoped_policy_requires_scope():
    engine = ScopedPolicyEngine(required_scopes={"tool_a": {"users:read"}}, config=RobynMCPConfig())
    ctx = RequestContext(scopes={"users:write"})
    import asyncio

    try:
        asyncio.run(_authorize(engine, "tool_a", ctx))
        assert False, "expected PermissionError"
    except PermissionError as exc:
        assert "users:read" in str(exc)
