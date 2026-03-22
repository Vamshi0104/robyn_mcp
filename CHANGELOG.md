# Changelog

All notable changes to this project will be documented in this file.

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
