from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool

# Quick curl checks after app.start(port=8080):
# 1) curl -X POST http://localhost:8080/mcp -H 'content-type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_products","arguments":{}}}'
# 2) curl -X POST http://localhost:8080/mcp -H 'content-type: application/json' -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"create_product","arguments":{"id":"sku-2","name":"sock","price":15}}}'
# 3) curl -X POST http://localhost:8080/mcp -H 'content-type: application/json' -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_products","arguments":{}}}'

app = Robyn(__file__)

_products = [
    {"id": "sku-1", "name": "shoe", "price": 99},
]


@app.get("/products")
@expose_tool(
    operation_id="list_products",
    summary="List products",
    side_effect=False,
    cache_tags=["products"],
)
def list_products():
    return {"items": list(_products)}


@app.post("/products")
@expose_tool(
    operation_id="create_product",
    summary="Create product",
    side_effect=True,
    invalidate_tags=["products"],
)
def create_product(id: str, name: str, price: int):
    _products.append({"id": id, "name": name, "price": price})
    return {"ok": True, "count": len(_products)}


mcp = RobynMCP(
    app,
    config=RobynMCPConfig(
        require_session=False,
        enable_response_cache=True,
        response_cache_ttl_seconds=120,
    ),
)
mcp.mount_http("/mcp")


if __name__ == "__main__":
    app.start(port=8080)
