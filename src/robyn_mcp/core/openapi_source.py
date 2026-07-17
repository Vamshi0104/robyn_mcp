from __future__ import annotations

import copy
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from robyn_mcp.core.naming import slugify_operation
from robyn_mcp.core.operations import (
    Operation,
    OperationRisk,
    classify_operation_risk,
    score_operation_contract,
)

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
INTERNAL_TAGS = {"internal", "private", "debug", "admin-only"}
WEAK_SCHEMA_METHODS = {"post", "put", "patch"}


@dataclass(slots=True)
class OpenAPIOperationReport:
    operations: list[Operation]
    recommended: list[str]
    approval_required: list[str]
    hidden: dict[str, str]
    scores: dict[str, dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "operationCount": len(self.operations),
            "recommendedToolCount": len(self.recommended),
            "approvalRequiredCount": len(self.approval_required),
            "hiddenCount": len(self.hidden),
            "recommendedTools": self.recommended,
            "approvalRequiredTools": self.approval_required,
            "hiddenOperations": self.hidden,
            "averageContractScore": round(
                sum(item["score"] for item in self.scores.values()) / len(self.scores),
                2,
            )
            if self.scores
            else None,
            "tools": [
                {
                    "name": operation.name,
                    "method": operation.method,
                    "path": operation.path,
                    "risk": operation.risk.value,
                    "tags": operation.tags,
                    "score": self.scores[operation.name]["score"],
                    "warnings": self.scores[operation.name]["warnings"],
                    "recommended": operation.name in self.recommended,
                    "approvalRequired": operation.name in self.approval_required,
                    "hiddenReason": self.hidden.get(operation.name),
                }
                for operation in self.operations
            ],
        }


def load_openapi_document(source: str | Path) -> dict[str, Any]:
    text: str
    source_text = str(source)
    if source_text.startswith(("http://", "https://")):
        with urllib.request.urlopen(source_text, timeout=10) as response:
            text = response.read().decode("utf-8")
    else:
        text = Path(source).read_text()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on optional PyYAML
            raise ValueError(
                "OpenAPI source must be JSON, or install PyYAML for YAML files"
            ) from exc
        parsed = yaml.safe_load(text)

    if not isinstance(parsed, dict) or not isinstance(parsed.get("paths"), dict):
        raise ValueError("OpenAPI document must be an object with a paths object")
    return parsed


def _resolve_ref(value: Any, document: dict[str, Any]) -> Any:
    if not isinstance(value, dict):
        return value
    ref = value.get("$ref")
    if isinstance(ref, str):
        if not ref.startswith("#/"):
            return value
        node: Any = document
        for part in ref.removeprefix("#/").split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                return value
            node = node[part]
        return _resolve_ref(copy.deepcopy(node), document)

    resolved: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            resolved[key] = _resolve_ref(item, document)
        elif isinstance(item, list):
            resolved[key] = [_resolve_ref(entry, document) for entry in item]
        else:
            resolved[key] = item
    return resolved


def _parameter_schema(parameter: dict[str, Any]) -> tuple[str, dict[str, Any], bool] | None:
    name = parameter.get("name")
    location = parameter.get("in")
    if not isinstance(name, str) or location not in {"path", "query", "header", "cookie"}:
        return None
    schema = copy.deepcopy(parameter.get("schema") or {"type": "string"})
    if not isinstance(schema, dict):
        schema = {"type": "string"}
    if parameter.get("description"):
        schema.setdefault("description", parameter["description"])
    schema.setdefault("x-mcp-source", location)
    return name, schema, bool(parameter.get("required") or location == "path")


def _request_schema(spec: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: set[str] = set()

    for parameter in spec.get("parameters") or []:
        if not isinstance(parameter, dict):
            continue
        resolved = _resolve_ref(parameter, document)
        parsed = _parameter_schema(resolved)
        if parsed is None:
            continue
        name, schema, is_required = parsed
        if schema.get("x-mcp-source") in {"header", "cookie"}:
            continue
        properties[name] = schema
        if is_required:
            required.add(name)

    request_body = spec.get("requestBody") or {}
    request_body = _resolve_ref(request_body, document)
    content = request_body.get("content") if isinstance(request_body, dict) else None
    if isinstance(content, dict):
        json_entry = content.get("application/json") or next(iter(content.values()), None)
        if isinstance(json_entry, dict):
            body_schema = _resolve_ref(copy.deepcopy(json_entry.get("schema") or {}), document)
            if isinstance(body_schema, dict) and body_schema.get("type") == "object":
                body_props = body_schema.get("properties") or {}
                if isinstance(body_props, dict):
                    for key, value in body_props.items():
                        if key in properties:
                            continue
                        if isinstance(value, dict):
                            value = copy.deepcopy(value)
                            value.setdefault("x-mcp-source", "body")
                        properties[str(key)] = value
                required.update(str(item) for item in body_schema.get("required") or [])
            elif body_schema:
                body_schema.setdefault("x-mcp-source", "body")
                properties["body"] = body_schema
                if request_body.get("required"):
                    required.add("body")

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = sorted(required)
    return schema


def _response_schema(spec: dict[str, Any], document: dict[str, Any]) -> dict[str, Any] | None:
    responses = spec.get("responses") or {}
    for status in ("200", "201", "202", "204", "default"):
        response = _resolve_ref(responses.get(status) or {}, document)
        content = response.get("content") if isinstance(response, dict) else None
        if not isinstance(content, dict):
            continue
        json_entry = content.get("application/json") or next(iter(content.values()), None)
        if isinstance(json_entry, dict) and json_entry.get("schema") is not None:
            schema = _resolve_ref(copy.deepcopy(json_entry["schema"]), document)
            return schema if isinstance(schema, dict) else None
    return None


def _fallback_operation_id(method: str, path: str) -> str:
    cleaned = re.sub(r"[{}]", "", path.strip("/"))
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", cleaned)
    return f"{method}_{cleaned or 'root'}"


def _operation_name(operation_id: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", operation_id)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return slugify_operation(value).lower()


def _security_scopes(spec: dict[str, Any], root_security: list[Any] | None = None) -> list[str]:
    security = spec.get("security")
    if security is None:
        security = root_security or []
    scopes: set[str] = set()
    for item in security or []:
        if not isinstance(item, dict):
            continue
        for scheme, values in item.items():
            scopes.add(str(scheme))
            if isinstance(values, list):
                scopes.update(str(value) for value in values)
    return sorted(scopes)


class OpenAPIOperationSource:
    def __init__(self, document: dict[str, Any]) -> None:
        self.document = document

    @classmethod
    def from_source(cls, source: str | Path) -> OpenAPIOperationSource:
        return cls(load_openapi_document(source))

    def discover(self) -> list[Operation]:
        operations: list[Operation] = []
        paths = self.document.get("paths") or {}
        root_security = (
            self.document.get("security") if isinstance(self.document.get("security"), list) else []
        )

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            path_parameters = path_item.get("parameters") or []
            for method, raw_spec in path_item.items():
                method_l = str(method).lower()
                if method_l not in HTTP_METHODS or not isinstance(raw_spec, dict):
                    continue
                spec = _resolve_ref(raw_spec, self.document)
                if not isinstance(spec, dict):
                    continue
                merged_spec = dict(spec)
                merged_spec["parameters"] = list(path_parameters) + list(
                    spec.get("parameters") or []
                )
                operation_id = str(
                    spec.get("operationId") or _fallback_operation_id(method_l, str(path))
                )
                name = _operation_name(operation_id)
                tags = [str(tag) for tag in spec.get("tags") or []]
                side_effect = method_l in {"post", "put", "patch", "delete"}
                description = (
                    spec.get("description") or spec.get("summary") or f"{method_l.upper()} {path}"
                )
                risk = classify_operation_risk(
                    name=name,
                    method=method_l,
                    path=str(path),
                    side_effect=side_effect,
                    idempotent=method_l in {"get", "put", "delete", "head", "options"},
                    tags=tags,
                )
                operations.append(
                    Operation(
                        name=name,
                        description=str(description),
                        input_schema=_request_schema(merged_spec, self.document),
                        output_schema=_response_schema(spec, self.document),
                        method=method_l.upper(),
                        path=str(path),
                        side_effect=side_effect,
                        auth_requirements=_security_scopes(spec, root_security),
                        tags=tags,
                        risk=risk,
                        metadata={
                            "operation_id": operation_id,
                            "deprecated": bool(spec.get("deprecated", False)),
                            "summary": spec.get("summary"),
                            "source": "openapi",
                        },
                    )
                )
        return operations


def analyze_operations(operations: list[Operation]) -> OpenAPIOperationReport:
    recommended: list[str] = []
    approval_required: list[str] = []
    hidden: dict[str, str] = {}
    scores: dict[str, dict[str, Any]] = {}

    for operation in operations:
        scores[operation.name] = score_operation_contract(operation)
        lower_tags = {tag.lower() for tag in operation.tags}
        if operation.metadata.get("deprecated"):
            hidden[operation.name] = "deprecated"
        elif lower_tags & INTERNAL_TAGS:
            hidden[operation.name] = "internal-tag"
        elif operation.method.lower() in WEAK_SCHEMA_METHODS and not operation.input_schema.get(
            "properties"
        ):
            hidden[operation.name] = "mutation-without-input-schema"

        if operation.risk in {
            OperationRisk.DATA_DELETION,
            OperationRisk.FINANCIAL_ACTION,
            OperationRisk.CREDENTIAL_ACTION,
            OperationRisk.ADMIN_ACTION,
            OperationRisk.EXTERNAL_COMMUNICATION,
            OperationRisk.IRREVERSIBLE_MUTATION,
        }:
            approval_required.append(operation.name)

        if (
            operation.name not in hidden
            and operation.risk in {OperationRisk.READ_ONLY, OperationRisk.SENSITIVE_DATA_ACCESS}
            and scores[operation.name]["score"] >= 70
        ):
            recommended.append(operation.name)

    return OpenAPIOperationReport(
        operations=operations,
        recommended=recommended,
        approval_required=approval_required,
        hidden=hidden,
        scores=scores,
    )


def inspect_openapi_source(source: str | Path) -> dict[str, Any]:
    operations = OpenAPIOperationSource.from_source(source).discover()
    return analyze_operations(operations).as_dict()
