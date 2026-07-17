# Architecture

## Runtime flow

1. Inspect Robyn routes and explicit decorators.
2. Build registries for tools, resources, and prompts.
3. Expose a single HTTP endpoint for MCP JSON-RPC.
4. Negotiate protocol/session behavior.
5. Resolve auth context and apply policy checks.
6. Execute the underlying handler.
7. Return protocol-compliant MCP content and audit metadata.

## Why the design is hybrid

FastAPI-centric designs can rely much more heavily on OpenAPI as a source of truth. For Robyn, a safer early design is hybrid:

- introspect what the framework exposes reliably
- allow explicit decorators to override unstable or missing metadata
- keep schema generation deterministic from type hints
