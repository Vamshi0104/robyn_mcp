from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool

app = Robyn(__file__)

@app.get("/billing/summary")
@expose_tool(summary="Get billing summary", requires_auth=True)
def get_billing_summary(tenant_id: str | None = None):
    if not tenant_id:
        return {
            "ok": False,
            "error": "tenant_id is required",
            "code": "missing_tenant_id",
        }

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "plan": "pro",
        "usage": 128,
        "status": "active",
    }

server = RobynMCP(
    app,
    config=RobynMCPConfig(
        require_session=True,
        enable_resources=False,
        enable_prompts=False,
    ),
)
server.mount_http("/mcp")

@app.get("/health")
def health():
    return {"ok": True}

if __name__ == "__main__":
    app.start(port=8080)