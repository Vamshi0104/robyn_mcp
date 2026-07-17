from __future__ import annotations

from typing import Any

from robyn_mcp.core.openapi_source import OpenAPIOperationSource
from robyn_mcp.core.operations import Operation


class FastAPIOperationSource:
    def __init__(self, app: Any) -> None:
        self.app = app

    def discover(self) -> list[Operation]:
        openapi = getattr(self.app, "openapi", None)
        if not callable(openapi):
            raise TypeError("FastAPIOperationSource requires an app with callable openapi()")
        document = openapi()
        if not isinstance(document, dict):
            raise ValueError("FastAPI openapi() must return a dictionary")
        return OpenAPIOperationSource(document).discover()
