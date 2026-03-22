from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig, expose_prompt, expose_resource

app = Robyn(__file__)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/products")
async def list_products():
    return [{"id": "p1", "name": "shoe"}]


@app.post("/orders")
async def create_order(product_id: str, qty: int):
    return {"ok": True, "product_id": product_id, "qty": qty}


@app.get("/context")
@expose_resource(uri="context://service/current", name="service-context")
async def current_context():
    return {"service": "robyn_mcp-demo"}


@app.get("/prompt/release")
@expose_prompt(name="release-summary")
async def release_prompt(service: str = "robyn_mcp"):
    return {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Write release notes for {service}."}
                ],
            }
        ]
    }


mcp = RobynMCP(
    app,
    config=RobynMCPConfig(
        enable_resources=True,
        enable_prompts=True,
        auto_expose_openapi=True,
        enable_playground=True,
        enable_tool_tracing=True,
    ),
)

mcp.mount_http("/mcp")

app.start(port=8080)