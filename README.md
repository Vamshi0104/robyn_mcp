
<h1 align="center">robyn-mcp</h1>

<p align="center">
  The Robyn reference adapter for turning existing APIs into governed MCP tools, resources, and prompts.
</p>

<p align="center">
  <a href="https://github.com/Vamshi0104/robyn_mcp/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Vamshi0104/robyn_mcp/actions/workflows/ci.yml/badge.svg?branch=main" /></a>
  <a href="https://pypi.org/project/robyn-mcp/"><img alt="PyPI" src="https://img.shields.io/badge/pypi-v1.0.3-blue" /></a>
  <a href="https://pypi.org/project/robyn-mcp/"><img src="https://img.shields.io/pypi/dm/robyn-mcp.svg" /></a>
  <a href="https://github.com/Vamshi0104/robyn_mcp/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue" /></a>
  <a href="https://vamshi0104.github.io/robyn_mcp/"><img src="https://img.shields.io/badge/docs-live-blue" /></a>
</p>

---

## Why robyn-mcp

You already have a Robyn backend.

You should not need to duplicate handlers, rewrite schemas, or rebuild authentication just to make it usable by AI agents.

**robyn-mcp is a production-minded bridge from existing APIs to governed MCP surfaces.**

- Convert existing Robyn routes into MCP tools
- Add resources and prompts without redesign
- Classify risky tools and surface approval metadata
- Keep your architecture intact
- Trace, audit, cache, and validate the endpoint before release

---

## 15-second demo

<!-- DEMO_GIF_START: add docs/assets/robyn_mcp_demo.gif after recording the launch demo. -->
Demo GIF placeholder: record the launch flow and add `docs/assets/robyn_mcp_demo.gif` here.
<!-- DEMO_GIF_END -->

```text
Existing Robyn API
    -> RobynMCP(app).mount_http("/mcp")
    -> Tools, resources, prompts, policies, traces
    -> Claude, ChatGPT, Cursor, VS Code, and MCP Inspector workflows
```

```python
from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool

app = Robyn(__file__)

@app.get("/customers/:customer_id")
@expose_tool(
    summary="Get customer profile",
    description="Read the customer profile for support workflows.",
    tags=["customer-support"],
    requires_auth=True,
    auth_scopes=["customer.read"],
)
def get_customer(customer_id: str):
    return {"customer_id": customer_id, "status": "active"}

mcp = RobynMCP(app, config=RobynMCPConfig(require_session=False))
mcp.mount_http("/mcp")
app.start(port=8080)
```

---

## Highlights

- Auto-expose Robyn routes as MCP tools
- JSON Schema generation from Python types
- OpenAPI enrichment and `$ref` resolution
- Framework-neutral OpenAPI operation inspection
- OpenAPI gateway invocation for safe upstream proxy experiments
- FastAPI OpenAPI adapter for evaluating non-Robyn APIs
- Auth-aware context with explicit header allowlists
- Risk classification and approval-required annotations
- Observability: metrics, traces, audit logs, recent events
- Response caching with tag invalidation
- CLI validation plus `robyn-mcp doctor`
- Built-in playground UI

---

## Installation

```bash
python -m pip install --upgrade pip
pip install robyn robyn-mcp
```

Optional local banner:

```bash
robyn-mcp install-note
```

Validate a live endpoint:

```bash
robyn-mcp doctor http://localhost:8080/mcp --json
```

Inspect an OpenAPI document before exposing it to agents:

```bash
robyn-mcp inspect-openapi ./openapi.json --json
```

The report includes recommended read tools, approval-required operations, hidden/internal operations, risk categories, and contract-quality warnings.

Invoke one OpenAPI operation against an upstream service:

```bash
robyn-mcp invoke-openapi ./openapi.json \
  --upstream http://localhost:8000 \
  --operation get_customer \
  --args '{"customer_id":"cus_123","expand":"orders"}' \
  --header 'Authorization: Bearer dev-token' \
  --json
```

Benchmark OpenAPI inspection and contract scoring:

```bash
robyn-mcp benchmark-openapi ./openapi.json --iterations 50 --json
```

Run the richer customer-support demo:

```bash
python examples/customer_support_app.py
robyn-mcp doctor http://localhost:8080/mcp --json
open http://localhost:8080/mcp/playground
```

---

## Quick Start

```python
from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool

app = Robyn(__file__)

@app.get("/health")
@expose_tool(summary="Return service health")
def health():
    return {"ok": True}

mcp = RobynMCP(app, config=RobynMCPConfig(require_session=False))
mcp.mount_http("/mcp")

app.start(port=8080)
```

---

## Compatibility and Protocol Status

`robyn-mcp` supports Streamable-HTTP style JSON-RPC dispatch, initialization, sessions, tools, optional resources, optional prompts, JSON-RPC error mapping, origin validation, content negotiation, and session deletion.

| Client | stdio | Streamable HTTP | Auth | Tools | Resources | Prompts |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Desktop | Planned | N/A | Configurable | Contract | Contract | Contract |
| Claude Code | Planned | Contract | Configurable | Contract | Contract | Contract |
| ChatGPT | N/A | Contract | Configurable | Contract | Contract | Needs repeatable test |
| Cursor | Planned | Contract | Configurable | Contract | Contract | Needs repeatable test |
| VS Code | Planned | Contract | Configurable | Contract | Contract | Needs repeatable test |
| MCP Inspector | Planned | Contract | Configurable | Contract | Contract | Contract |

Only promote a cell to "verified" after a repeatable test or CI fixture proves it. See `docs/compatibility_matrix.md` and `robyn-mcp runtime --json`.

---

## Governance Layer

robyn-mcp keeps generated MCP surfaces reviewable before agents use them:

- Framework-neutral `Operation` model and adapter contracts
- OpenAPI `OperationSource` for framework-neutral inspection
- `OpenAPIGatewayInvoker` for path/query/body splitting and allowlist-based upstream headers
- `FastAPIOperationSource` for consuming FastAPI `app.openapi()` output
- Risk categories for deletion, financial, credential, admin, sensitive-data, and external-communication tools
- Approval-required metadata for dangerous operations
- Tool contract scoring for names, descriptions, schemas, output schemas, and safety configuration
- Compatibility and protocol reports for release review

---

## Security Defaults

- Header forwarding is allowlist-based by default.
- Cookies are not forwarded unless explicitly configured.
- Response redaction can remove sensitive fields from returned payloads.
- Origin validation can be enforced with `allowed_origins`.
- Rate limiting is available through the built-in token bucket policy engine.
- Destructive and sensitive tools now carry risk metadata in tool annotations.

Production checklist: `docs/security.md`

## 🗂️ Response Caching With Invalidation Tags

```python
from robyn_mcp import RobynMCPConfig, expose_tool

@expose_tool(operation_id="list_products", side_effect=False, cache_tags=["products"])
def list_products():
    return {"items": [...]}

@expose_tool(operation_id="create_product", side_effect=True, invalidate_tags=["products"])
def create_product(id: str, name: str, price: int):
    ...

config = RobynMCPConfig(
    require_session=False,
    enable_response_cache=True,
    response_cache_ttl_seconds=120,
)
```

Cache behavior:
- Read tools can be cached with TTL.
- Mutation tools can invalidate matching cache tags.
- If no invalidation tags are provided on a mutation, cache is safely cleared by default.

Curl flow:

```bash
# 1) Read (cached after first call)
curl -X POST http://localhost:8080/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_products","arguments":{}}}'

# 2) Mutation (invalidates products cache tag)
curl -X POST http://localhost:8080/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"create_product","arguments":{"id":"sku-2","name":"sock","price":15}}}'

# 3) Read again (fresh result after invalidation)
curl -X POST http://localhost:8080/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_products","arguments":{}}}'
```

See complete runnable example: `examples/cache_invalidation_example.py`.

---

## 🧪 Test

```bash
curl -X POST http://localhost:8080/mcp \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

---

## 🛠 CLI

```bash
robyn-mcp runtime --json
robyn-mcp validate-endpoint http://localhost:8080/mcp
robyn-mcp doctor http://localhost:8080/mcp --json
robyn-mcp inspect-openapi ./openapi.json --json
robyn-mcp invoke-openapi ./openapi.json --upstream http://localhost:8000 --operation get_customer --args '{}'
robyn-mcp benchmark-openapi ./openapi.json --iterations 25 --json
robyn-mcp compare-benchmarks benchmarks/robyn_sample.json benchmarks/fastapi_sample.json --json
robyn-mcp publish-benchmarks benchmarks/robyn_sample.json benchmarks/fastapi_sample.json --out benchmark_report.md
robyn-mcp release-audit --json
robyn-mcp release-bundle --json
```

---

## 🖥 Playground

Enable:

```python
RobynMCPConfig(enable_playground=True)
```

Open:

```
/mcp/playground
```

---

## 📊 Observability

- Tool call metrics  
- Error tracking  
- Latency stats  
- Audit logs  
- Recent traces  

---

## 📁 Structure

```
robyn_mcp/
├── src/
├── tests/
├── examples/
└── scripts/
```

---

## 🧠 Core Concepts

| Concept   | Description |
|----------|------------|
| Tools    | Callable MCP endpoints |
| Resources| Structured data sources |
| Prompts  | Reusable prompt templates |


## Current capabilities

- Route to MCP tool harvesting
- Explicit decorators for tools, resources, and prompts
- JSON Schema generation from Python annotations
- OpenAPI-aware enrichment when route metadata exists
- OpenAPI spec inspection, benchmark reporting, and upstream operation invocation
- FastAPI OpenAPI document adapter for framework-neutral operation discovery
- Streamable-HTTP style single-endpoint dispatch foundation
- Session lifecycle support with TTL
- Request context, principal, tenant, and header forwarding hooks
- Per-tool policy hooks and built-in token-bucket rate limiting
- Response caching for read tools with tag-based invalidation on mutations
- Metrics and recent audit event capture
- Docs, CI, release workflow, smoke tests, and benchmark scaffolding

---

## Final Note

Adopting MCP shouldn’t require rebuilding your backend.

With **robyn-mcp**, your existing Robyn routes become a discoverable, inspectable, policy-aware MCP surface.

Contributions are welcome. Start with `CONTRIBUTING.md` and the client verification issue template.
