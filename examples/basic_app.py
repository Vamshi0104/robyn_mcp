from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig, expose_prompt, expose_resource, expose_tool

app = Robyn(__file__)


@app.get("/health")
@expose_tool(summary="Return service health")
def health():
    return {"ok": True}


@app.get("/context")
@expose_resource(uri="context://service/current", name="service-context")
def context():
    return {"service": "robyn_mcp-demo"}


@app.get("/prompt/release")
@expose_prompt(name="release-summary")
def release_prompt(service: str = "robyn_mcp"):
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
        require_session=False,
        enable_resources=True,
        enable_prompts=True,
    ),
)
mcp.mount_http("/mcp")


if __name__ == "__main__":
    app.start(port=8080)