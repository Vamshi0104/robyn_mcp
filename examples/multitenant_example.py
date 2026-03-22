from robyn import Robyn
from robyn_mcp import RobynMCP, RobynMCPConfig, expose_resource, expose_tool

app = Robyn(__file__)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/tenant/profile")
@expose_resource(uri="context://tenant/profile", name="tenant-profile")
def tenant_profile():
    return {"tenant": "tenant-123", "plan": "pro"}


@app.post("/invoices")
@expose_tool(summary="Create invoice", requires_auth=True, side_effect=True)
def create_invoice(
    customer_id: str | None = None,
    amount: float | int | None = None,
    request=None,
):
    headers = {}
    if request is not None:
        headers = getattr(request, "headers", {}) or {}

    auth_header = headers.get("authorization") if isinstance(headers, dict) else None
    tenant_id = headers.get("x-tenant-id") if isinstance(headers, dict) else None

    if not auth_header:
        return {
            "ok": False,
            "error": "authentication required",
            "code": "missing_auth",
        }

    if not tenant_id:
        return {
            "ok": False,
            "error": "tenant_id is required",
            "code": "missing_tenant_id",
        }

    if not customer_id:
        return {
            "ok": False,
            "error": "customer_id is required",
            "code": "missing_customer_id",
        }

    if amount is None:
        return {
            "ok": False,
            "error": "amount is required",
            "code": "missing_amount",
        }

    if not isinstance(amount, (int, float)):
        return {
            "ok": False,
            "error": "amount must be a number",
            "code": "invalid_amount_type",
        }

    if float(amount) <= 0:
        return {
            "ok": False,
            "error": "amount must be greater than 0",
            "code": "invalid_amount_value",
        }

    return {
        "ok": True,
        "invoice_id": "inv_demo_001",
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "amount": float(amount),
        "status": "created",
    }


server = RobynMCP(
    app,
    config=RobynMCPConfig(
        require_session=True,
        enable_resources=True,
        enable_prompts=False,
    ),
)
server.mount_http("/mcp")


if __name__ == "__main__":
    app.start(port=8080)