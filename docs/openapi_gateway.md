# OpenAPI Source and Gateway

`robyn-mcp` includes a framework-neutral OpenAPI operation source plus an upstream gateway invoker. Teams can inspect an API contract, score the MCP surface it would generate, and invoke selected operations against a real upstream service during controlled testing.

## Inspect a Spec

```bash
robyn-mcp inspect-openapi ./openapi.json --json
```

The command reports:

- total operations discovered
- recommended tools
- approval-required tools
- hidden/internal operations
- operation risk categories
- contract quality scores
- schema and description warnings

## Invoke an Operation

```bash
robyn-mcp invoke-openapi ./openapi.json \
  --upstream http://localhost:8000 \
  --operation get_customer \
  --args '{"customer_id":"cus_123","expand":"orders"}' \
  --header 'Authorization: Bearer dev-token' \
  --json
```

The gateway uses the OpenAPI contract to split arguments into:

- path parameters
- query parameters
- JSON request body fields

Forwarded headers are explicit. The default allowlist includes `authorization`, `x-request-id`, and `x-tenant-id`. Cookies are not forwarded by default.

HTTP error responses are returned as structured invocation results instead of crashing the caller. Network errors are also returned as structured error payloads so local tools can display a useful failure.

## Benchmark Inspection

```bash
robyn-mcp benchmark-openapi ./openapi.json --iterations 50 --json
```

The benchmark reports operation count plus min, mean, median, and max inspection time. Use it when comparing large OpenAPI contracts or tracking schema inspection regressions.

## FastAPI Adapter

FastAPI apps can be inspected through their generated OpenAPI document:

```python
from robyn_mcp import FastAPIOperationSource

operations = FastAPIOperationSource(app).discover()
```

This does not require `robyn-mcp` to import FastAPI directly; the adapter only expects an object with a callable `openapi()` method.

## What It Does

The source reads OpenAPI 3.x JSON documents, and YAML when PyYAML is installed. It resolves local `$ref` values, merges path/query parameters with JSON request bodies, extracts response schemas, and classifies risk.

Risk categories include:

- `read_only`
- `sensitive_data_access`
- `idempotent_mutation`
- `reversible_mutation`
- `data_deletion`
- `financial_action`
- `credential_action`
- `admin_action`
- `external_communication`

## Least-Privilege Defaults

The report hides or warns about operations that are:

- deprecated
- tagged as `internal`, `private`, `debug`, or `admin-only`
- mutating without an input schema

Dangerous operations are not automatically recommended. They are marked as approval-required so teams can add policy before giving agents access.

## Why This Matters

OpenAPI inspection lets API teams evaluate how their existing API would look as an MCP surface before writing adapter code.

Gateway invocation makes the evaluation concrete: teams can test one operation at a time, preserve least-privilege header forwarding, and add policy before broad agent access.
