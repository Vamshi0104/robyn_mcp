
<h1 align="center">robyn-mcp</h1>

<p align="center">
  Turn Robyn APIs into MCP tools, resources, and prompts instantly.
</p>

<p align="center">
  <a href="https://pypi.org/project/robyn-mcp/"><img src="https://img.shields.io/pypi/v/robyn-mcp.svg" /></a>
  <a href="https://pypi.org/project/robyn-mcp/"><img src="https://img.shields.io/pypi/dm/robyn-mcp.svg" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/your-org/robyn_mcp" /></a>
  <a href="https://vamshi0104.github.io/robyn_mcp/"><img src="https://img.shields.io/badge/docs-live-blue" /></a>
</p>

---

##  Why robyn-mcp

You already have a Robyn backend.

You shouldn’t need to rebuild it to support MCP.

**robyn-mcp bridges that gap.**

- Convert existing routes → MCP tools
- Add resources & prompts without redesign
- Keep your architecture intact
- Ship production-ready MCP instantly

---

## 🚀 Highlights

- ⚡ Auto-expose Robyn routes as MCP tools  
- 🧠 JSON Schema generation from Python types  
- 🔗 OpenAPI enrichment + `$ref` resolution  
- 🔐 Auth-aware context + header forwarding  
- 📊 Observability (metrics, traces, audit logs)  
- 🧪 CLI for validation + debugging  
- 🖥️ Built-in Playground UI  
- 📦 Production-ready packaging  

---

## 📦 Installation

```bash
pip install robyn robyn-mcp
```

---

## ⚡ Quick Start

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
robyn-mcp validate-endpoint --url http://localhost:8080/mcp
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
- Streamable-HTTP style single-endpoint dispatch foundation
- Session lifecycle support with TTL
- Request context, principal, tenant, and header forwarding hooks
- Per-tool policy hooks and built-in token-bucket rate limiting
- Metrics and recent audit event capture
- Docs, CI, release workflow, smoke tests, and benchmark scaffolding

---

## Final Note

Adopting MCP shouldn’t require rebuilding your backend.

With **robyn-mcp**, your existing Robyn routes become a fully discoverable, inspectable, and production-ready MCP surface - with minimal effort and maximum leverage.
