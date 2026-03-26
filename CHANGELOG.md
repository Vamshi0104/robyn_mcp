# Changelog

All notable changes to this project will be documented in this file.

## 1.0.1

### Added
- Install banner output with ASCII styling for `ROBYN-MCP`, including author, license, and created date metadata.
- New CLI command: `robyn-mcp install-note` to print the install banner and release metadata on demand.
- Runtime startup banner integration in `RobynMCP`, printed once by default when the app starts.
- Runtime banner fallback for app objects where `start` cannot be monkey-patched (prints once during `RobynMCP` initialization).
- Post-install banner verification step in `scripts/verify_install.py` after upgrading pip and installing the built wheel.
- Response caching for read tools with configurable TTL and max entries.
- Tag-based cache invalidation for mutation tools, with safe full-cache invalidation fallback.
- Coverage tests for cache hits, context isolation, tagged invalidation, and fallback invalidation.
- Coverage tests for install-note output, startup banner behavior, disable flag behavior, and non-writable-start fallback behavior.

### Changed
- Bumped project version from `1.0.0` to `1.0.1` across package metadata, runtime config defaults, and tests.
- Updated website `index.html` release callouts to show the `v1.0.1` download label.
- Updated README and examples with cache configuration and curl workflow documentation.
- Documented that standard `pip install robyn-mcp` wheel installs do not execute package post-install Python hooks, and that `python -m robyn_mcp.cli install-note` is the reliable explicit banner step.

## 1.0.0

### Added
- OpenAPI-based MCP tool auto-generation for Robyn routes.
- Optional MCP resources and prompts support.
- Tool tracing, metrics, and recent tool event reporting.
- Local playground UI for inspecting metadata, listing tools, and calling methods.
- CLI commands for endpoint validation, inspection, runtime metadata, and debug snapshots.
- Documentation for quickstart, compatibility, deployment, benchmarking, and release workflows.

### Improved
- JSON-RPC parse error handling now returns a structured `-32700` response instead of a generic server failure.
- Session lifecycle, transport behavior, and local end-to-end validation coverage.
- Packaging and release flow for PyPI and GitHub-based distribution.

### Notes
- Default configuration is intended to be safe for production publishing: advanced exposure features should be enabled explicitly.
- The recommended full-feature local config is:

```python
RobynMCPConfig(
    enable_resources=True,
    enable_prompts=True,
    auto_expose_openapi=True,
    enable_playground=True,
    enable_tool_tracing=True,
)
```

## 0.16.0
- Added release audit tooling and improved release preparation workflow.

## 0.14.0
- Added broader editor and packaging support.

## 0.8.0
- Added OpenAPI harvesting improvements with merged parameter and body schema support.
