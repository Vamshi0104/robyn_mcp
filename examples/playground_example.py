from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig, expose_tool

app = Robyn(__file__)

@app.get("/health")
@expose_tool(summary="Return service health")
def health():
    return {"ok": True}

mcp = RobynMCP(
    app,
    config=RobynMCPConfig(
        require_session=False,
        enable_playground=True,
    ),
)
mcp.mount_http("/mcp")

if __name__ == "__main__":
    app.start(port=8080)