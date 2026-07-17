# Quickstart

## Install

```bash
pip install robyn-mcp
```

## Minimal app

```python
from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool

app = Robyn(__file__)

@app.get("/greet")
@expose_tool(summary="Return a greeting")
def greet(name: str = "world"):
    return {"message": f"Hello, {name}!"}

mcp = RobynMCP(app, config=RobynMCPConfig(require_session=False))
mcp.mount_http("/mcp")
app.start(port=8080)
```

## Discover tools

```bash
curl -X POST http://localhost:8080/mcp   -H 'content-type: application/json'   -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Call a tool

```bash
curl -X POST http://localhost:8080/mcp   -H 'content-type: application/json'   -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"greet","arguments":{"name":"Vamshi"}}}'
```

## Next steps

- add `@expose_resource(...)` for read-only contextual data
- add `@expose_prompt(...)` for reusable prompt templates
- plug in a principal extractor or custom policy
- add metrics export to your observability stack
