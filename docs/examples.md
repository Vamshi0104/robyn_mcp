# Examples

The `examples/` folder includes runnable demos for the most important adoption paths.

## Customer Support App

`examples/customer_support_app.py` is the recommended demo for screenshots, videos, and first-time users. It includes:

- one read-only health tool
- one authenticated customer lookup tool
- one risky billing/refund action
- one support playbook resource
- one escalation prompt
- playground, tracing, resources, prompts, and response cache enabled

Run it:

```bash
python examples/customer_support_app.py
robyn-mcp doctor http://localhost:8080/mcp --json
```

Then open:

```text
http://localhost:8080/mcp/playground
```

## OpenAPI Gateway Demo

Use `examples/openapi_demo_server.py` with `examples/openapi.json` to test OpenAPI inspection, benchmarking, and upstream invocation.

```bash
python examples/openapi_demo_server.py
robyn-mcp inspect-openapi examples/openapi.json --json
robyn-mcp invoke-openapi examples/openapi.json \
  --upstream http://127.0.0.1:8098 \
  --operation get_customer \
  --args '{"customer_id":"cus_123","expand":"orders"}' \
  --json
robyn-mcp benchmark-openapi examples/openapi.json --iterations 25 --json
```

## Smaller Examples

- `basic_app.py` — one-file demo for local testing.
- `auth_example.py` — principal extraction and authenticated tool metadata.
- `multitenant_example.py` — tenant-aware request context patterns.
- `cache_invalidation_example.py` — response cache and mutation invalidation tags.
- `openapi_auto_example.py` — OpenAPI-assisted route exposure.
- `playground_example.py` — local playground flow.
