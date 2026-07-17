from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from robyn_mcp.core.openapi_source import OpenAPIOperationSource, inspect_openapi_source


def _subprocess_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src = str(project_root / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not existing else src + os.pathsep + existing
    return env


def _write_openapi(tmp_path: Path) -> Path:
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "Shop API", "version": "1.0.0"},
        "security": [{"bearerAuth": []}],
        "paths": {
            "/customers/{customer_id}": {
                "get": {
                    "operationId": "getCustomer",
                    "summary": "Get customer profile",
                    "description": "Read a customer profile for support workflows.",
                    "tags": ["support"],
                    "parameters": [
                        {
                            "name": "customer_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Unique customer id.",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Customer",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Customer"}
                                }
                            },
                        }
                    },
                },
                "delete": {
                    "operationId": "deleteCustomer",
                    "summary": "Delete customer",
                    "description": "Delete a customer account after approval.",
                    "tags": ["admin"],
                    "responses": {"204": {"description": "Deleted"}},
                },
            },
            "/internal/debug": {
                "get": {
                    "operationId": "debugState",
                    "summary": "Debug state",
                    "tags": ["internal"],
                    "responses": {"200": {"description": "Debug"}},
                }
            },
            "/orders": {
                "post": {
                    "operationId": "createInvoice",
                    "summary": "Create invoice",
                    "description": "Create a customer invoice for a submitted order.",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"order_id": {"type": "string"}},
                                    "required": ["order_id"],
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            },
        },
        "components": {
            "schemas": {
                "Customer": {
                    "type": "object",
                    "properties": {"customer_id": {"type": "string"}, "status": {"type": "string"}},
                }
            }
        },
    }
    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(spec))
    return path


def test_openapi_operation_source_discovers_risk_and_schemas(tmp_path):
    path = _write_openapi(tmp_path)
    operations = OpenAPIOperationSource.from_source(path).discover()
    by_name = {operation.name: operation for operation in operations}

    assert set(by_name) == {"get_customer", "delete_customer", "debug_state", "create_invoice"}
    assert by_name["get_customer"].input_schema["required"] == ["customer_id"]
    assert by_name["get_customer"].output_schema["properties"]["status"]["type"] == "string"
    assert by_name["delete_customer"].risk.value == "data_deletion"
    assert by_name["create_invoice"].risk.value == "financial_action"


def test_inspect_openapi_source_reports_recommendations_and_hidden_tools(tmp_path):
    payload = inspect_openapi_source(_write_openapi(tmp_path))
    assert payload["operationCount"] == 4
    assert "get_customer" in payload["recommendedTools"]
    assert "delete_customer" in payload["approvalRequiredTools"]
    assert payload["hiddenOperations"]["debug_state"] == "internal-tag"
    assert payload["averageContractScore"] is not None


def test_inspect_openapi_cli_json(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robyn_mcp.cli",
            "inspect-openapi",
            str(_write_openapi(tmp_path)),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_subprocess_env(root),
    )
    payload = json.loads(result.stdout)
    assert payload["operationCount"] == 4
    assert payload["approvalRequiredCount"] >= 2
