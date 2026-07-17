from __future__ import annotations

from robyn import Robyn

from robyn_mcp import RobynMCP, RobynMCPConfig, expose_prompt, expose_resource, expose_tool

app = Robyn(__file__)


CUSTOMERS = {
    "cus_123": {
        "customer_id": "cus_123",
        "name": "Avery Chen",
        "plan": "enterprise",
        "status": "active",
        "open_tickets": 2,
    }
}


@app.get("/health")
@expose_tool(
    summary="Return service health",
    description="Read service health for local MCP validation and release checks.",
    tags=["ops"],
)
def health():
    return {"ok": True}


@app.get("/customers/:customer_id")
@expose_tool(
    summary="Get customer profile",
    description="Read a customer profile for support triage and account review workflows.",
    tags=["customer-support"],
    requires_auth=True,
    auth_scopes=["customer.read"],
)
def get_customer(customer_id: str):
    return CUSTOMERS.get(customer_id, {"customer_id": customer_id, "status": "unknown"})


@app.post("/customers/:customer_id/refund")
@expose_tool(
    summary="Create customer refund",
    description="Create a customer refund request after an operator has reviewed the account.",
    tags=["billing", "customer-support"],
    requires_auth=True,
    auth_scopes=["billing.refund"],
    side_effect=True,
)
def create_refund(customer_id: str, amount_cents: int, reason: str):
    return {
        "customer_id": customer_id,
        "refund_id": "ref_demo_001",
        "amount_cents": amount_cents,
        "reason": reason,
        "status": "pending_review",
    }


@expose_resource(
    uri="support://playbook/refunds",
    name="Refund playbook",
    description="Internal refund review checklist for support agents.",
    mime_type="text/markdown",
)
def refund_playbook():
    return (
        "# Refund Playbook\n\n"
        "1. Confirm customer identity.\n"
        "2. Review open tickets and account status.\n"
        "3. Create refund requests only after policy review.\n"
    )


@expose_prompt(
    name="summarize-customer",
    description="Draft a concise customer-support summary before escalation.",
)
def summarize_customer(customer_id: str, audience: str = "support lead"):
    return {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Summarize customer {customer_id} for {audience}. "
                            "Include status, open issues, and recommended next action."
                        ),
                    }
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
        enable_playground=True,
        enable_tool_tracing=True,
        enable_response_cache=True,
    ),
)
mcp.mount_http("/mcp")


if __name__ == "__main__":
    app.start(port=8080)

