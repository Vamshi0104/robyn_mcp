from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig

app = Robyn(__file__)

@app.get("/products")
def list_products():
    return [{"id": "p1", "name": "shoe"}]

@app.post("/orders")
def create_order(product_id: str, qty: int):
    return {"ok": True, "product_id": product_id, "qty": qty}

@app.get("/health")
def health():
    return {"ok": True}

mcp = RobynMCP(
    app,
    config=RobynMCPConfig(
        require_session=False,
        auto_expose_openapi=True,
    ),
)
mcp.mount_http("/mcp")

if __name__ == "__main__":
    app.start(port=8080)