# Benchmarks

robyn-mcp includes local benchmark helpers for release regression checks and comparison reports.

## OpenAPI inspection

Measure OpenAPI operation discovery and contract scoring:

```bash
robyn-mcp benchmark-openapi examples/openapi.json --iterations 50 --json
```

The JSON output includes the source, iteration count, operation count, min/mean/median/max duration, and the final inspection report.

## Comparison reports

Compare two benchmark JSON files:

```bash
robyn-mcp compare-benchmarks benchmarks/robyn_sample.json benchmarks/fastapi_sample.json --json
```

Render a markdown report:

```bash
robyn-mcp publish-benchmarks benchmarks/robyn_sample.json benchmarks/fastapi_sample.json --out benchmark_report.md
```

## Current benchmark targets

- OpenAPI inspection and contract scoring latency
- registry/discovery overhead
- tool-call dispatch overhead
- auth/policy hook overhead
- schema generation latency for larger handlers

Benchmarks in this repository are intentionally local and reproducible; they are meant for regression tracking, not public bragging numbers.
