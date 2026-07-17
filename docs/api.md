# API overview

## Public imports

```python
from robyn_mcp import (
    RobynMCP,
    RobynMCPConfig,
    expose_tool,
    expose_resource,
    expose_prompt,
)
```

## Main runtime objects

### `RobynMCP`

Main server façade. It harvests metadata, resolves registries, dispatches MCP JSON-RPC methods, and mounts the HTTP endpoint into a Robyn app.

### `RobynMCPConfig`

Configuration object for route filtering, session policy, auth forwarding, protocol negotiation, rate limiting, and compatibility behavior.

### `expose_tool`

Decorator for explicitly marking a Robyn handler as an MCP tool and attaching metadata such as summary, tags, name overrides, and policy hints.

### `expose_resource`

Decorator for exposing read-oriented resources with a fixed URI and metadata.

### `expose_prompt`

Decorator for exposing reusable MCP prompts.
