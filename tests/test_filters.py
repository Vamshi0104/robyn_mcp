from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.core.filters import FilterEngine
from robyn_mcp.core.models import RouteMetadata


def test_filter_include_tags() -> None:
    config = RobynMCPConfig(include_tags={"public"})
    route = RouteMetadata(
        path="/hello",
        method="get",
        handler=lambda: None,
        operation_id="hello",
        tags=["public"],
    )
    assert FilterEngine(config).allow(route) is True
