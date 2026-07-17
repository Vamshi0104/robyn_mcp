# Compatibility

## Runtime posture

`robyn_mcp` supports **contract-only** validation without Robyn installed and **live** validation when Robyn is present in the environment.

## Latest known upstream baseline

As of March 2026, Robyn's public releases page lists **v0.79.0** as the latest release, with several recent fixes around routing, JSON handling, cookies, SSE, and OpenAPI behavior. This is the baseline release line we target for public launch validation.

## MCP protocol versions

- 2025-03-26
- 2025-06-18
- 2025-11-25

HTTP is the primary transport posture. Legacy SSE remains explicit opt-in.

## What we validate

- tool discovery
- `initialize`, `tools/list`, `tools/call`
- resource and prompt capability exposure when enabled
- session lifecycle
- origin and accept-header handling
- OpenAPI harvesting and schema generation
- claim-aware auth propagation

## Live validation strategy

Run the optional Robyn integration tests in CI on a matrix that includes the latest supported Robyn release line and your target Python versions.
