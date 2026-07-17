# robyn_mcp

`robyn_mcp` is a Robyn-native adapter for the Model Context Protocol. It is built for teams that already have Robyn endpoints and want to expose those capabilities to AI clients as MCP tools, resources, and prompts without rewriting the application around manual MCP handlers.

## Product position

The public Robyn release notes show native MCP support inside the framework itself, including `app.mcp.resource(...)` and `app.mcp.tool(...)`. That means the strategic gap is a reusable **adapter layer** that can discover existing handlers, preserve schema intent, apply security policy, and ship with strong packaging and docs instead of asking every team to rebuild that layer internally.

## Project principles

- Robyn-native before framework-generic abstractions
- Explicit overrides where introspection is weak
- Secure defaults for header and cookie propagation
- Stable naming and compatibility reporting for AI clients
- Incremental path from proof-of-concept to production package

## Current release focus

- Robyn route harvesting into MCP tools, resources, and prompts
- OpenAPI operation inspection with local `$ref` resolution
- OpenAPI gateway invocation for controlled upstream tests
- FastAPI OpenAPI document adapter
- Endpoint validation, conformance-oriented doctor checks, and release audit tooling
- Benchmark helpers for OpenAPI inspection and endpoint comparisons
- Public release, PyPI, client verification, and community launch checklists
