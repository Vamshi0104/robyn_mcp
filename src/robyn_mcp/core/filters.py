from __future__ import annotations

from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.core.models import RouteMetadata


class FilterEngine:
    def __init__(self, config: RobynMCPConfig) -> None:
        self.config = config

    def allow(self, meta: RouteMetadata) -> bool:
        if not meta.exposed:
            return False
        if self.config.include_operations and meta.operation_id not in self.config.include_operations:
            return False
        if self.config.exclude_operations and meta.operation_id in self.config.exclude_operations:
            return False
        if self.config.include_tags and not (set(meta.tags) & self.config.include_tags):
            return False
        if self.config.exclude_tags and (set(meta.tags) & self.config.exclude_tags):
            return False
        return True
