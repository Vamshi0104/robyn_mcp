from __future__ import annotations

from robyn_mcp import OperationRisk, RobynMCP, RobynMCPConfig, expose_tool
from robyn_mcp.core.operations import Operation, classify_operation_risk, score_operation_contract
from robyn_mcp.testing.doctor import run_doctor


class FakeRoute:
    def __init__(self, path: str, method: str, handler) -> None:
        self.route = path
        self.route_type = method
        self.handler = handler


class FakeApp:
    def __init__(self, routes):
        self.routes = routes


@expose_tool(
    operation_id="delete_customer",
    summary="Delete customer",
    description="Delete a customer account after an operator approval has been recorded.",
    side_effect=True,
    approval_required=True,
)
def delete_customer(customer_id: str):
    return {"deleted": customer_id}


def test_operation_risk_classification_marks_deletes_as_approval_risks():
    risk = classify_operation_risk(
        name="delete_customer",
        method="delete",
        path="/customers/{customer_id}",
        side_effect=True,
    )
    assert risk is OperationRisk.DATA_DELETION


def test_server_surfaces_operation_readiness_and_tool_annotations():
    server = RobynMCP(
        FakeApp([FakeRoute("/customers/{customer_id}", "DELETE", delete_customer)]),
        config=RobynMCPConfig(require_session=False, show_banner_on_start=False),
    )
    tool = server.list_tools()[0]
    assert tool.annotations["risk"] == "data_deletion"
    assert tool.annotations["approvalRequired"] is True
    assert tool.annotations["contractQuality"]["score"] >= 70

    report = server.operation_readiness_report()
    assert report["operationCount"] == 1
    assert report["approvalRequiredTools"] == ["delete_customer"]


def test_contract_score_warns_on_weak_schema_and_description():
    payload = score_operation_contract(
        Operation(
            name="get",
            description="Gets",
            input_schema={},
            method="GET",
            path="/items/{id}",
        )
    )
    assert payload["score"] < 70
    assert payload["warnings"]


def test_doctor_report_shape_for_unreachable_endpoint():
    report = run_doctor("http://127.0.0.1:9/mcp", timeout=0.1).as_dict()
    assert report["ok"] is False
    assert report["score"] < 100
    assert any(check["name"] == "metadata" for check in report["checks"])
