# Roadmap

The immediate goal is to make `robyn-mcp` a credible reference adapter while evolving the architecture toward governed API-to-MCP infrastructure.

## Now

- Ship `1.0.2` with framework-neutral operation contracts.
- Publish clearer GitHub Pages and README positioning.
- Add `robyn-mcp doctor` as a conformance seed.
- Keep PyPI release steps reproducible and token-safe.

## Next

- Integrate the official MCP Python SDK where it can own lifecycle and transport semantics.
- Add stdio transport and repeatable client compatibility tests.
- Add OpenAPI gateway MVP.
- Move Robyn discovery behind a formal adapter boundary.

## Later

- Add FastAPI, Flask, and Django adapters.
- Add policy-as-code, approvals, shadow mode, replay, OpenTelemetry, and conformance badges.
- Build a plugin ecosystem for adapters, auth, policy, and observability.
