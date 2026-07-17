from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from robyn_mcp.core.models import RequestContext


class OperationRisk(str, Enum):
    READ_ONLY = "read_only"
    IDEMPOTENT_MUTATION = "idempotent_mutation"
    REVERSIBLE_MUTATION = "reversible_mutation"
    IRREVERSIBLE_MUTATION = "irreversible_mutation"
    FINANCIAL_ACTION = "financial_action"
    DATA_DELETION = "data_deletion"
    CREDENTIAL_ACTION = "credential_action"
    ADMIN_ACTION = "admin_action"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    EXTERNAL_COMMUNICATION = "external_communication"


@dataclass(slots=True)
class Operation:
    name: str
    description: str
    input_schema: dict[str, Any]
    method: str
    path: str
    output_schema: dict[str, Any] | None = None
    side_effect: bool = False
    auth_requirements: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    risk: OperationRisk = OperationRisk.READ_ONLY
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InvocationResult:
    value: Any
    status_code: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PolicyDecision:
    effect: str
    reason: str | None = None
    approval_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class OperationSource(Protocol):
    def discover(self) -> list[Operation]: ...


@runtime_checkable
class OperationInvoker(Protocol):
    async def invoke(
        self,
        operation: Operation,
        arguments: dict[str, Any],
        context: RequestContext,
    ) -> InvocationResult: ...


@runtime_checkable
class PolicyEvaluator(Protocol):
    async def evaluate(
        self,
        operation: Operation,
        context: RequestContext,
    ) -> PolicyDecision: ...


DELETION_TOKENS = ("delete", "remove", "destroy", "purge", "erase", "drop")
FINANCIAL_TOKENS = ("invoice", "payment", "charge", "refund", "payout", "transfer")
CREDENTIAL_TOKENS = ("token", "secret", "password", "credential", "api_key", "apikey")
ADMIN_TOKENS = ("admin", "permission", "role", "user_role", "tenant")
EXTERNAL_COMMUNICATION_TOKENS = ("email", "sms", "notify", "webhook", "send")
SENSITIVE_TOKENS = ("customer", "user", "account", "pii", "profile", "ssn")


def classify_operation_risk(
    *,
    name: str,
    method: str,
    path: str,
    side_effect: bool,
    idempotent: bool | None = None,
    tags: list[str] | None = None,
) -> OperationRisk:
    haystack = " ".join([name, method, path, " ".join(tags or [])]).lower()

    if any(token in haystack for token in DELETION_TOKENS):
        return OperationRisk.DATA_DELETION
    if any(token in haystack for token in FINANCIAL_TOKENS):
        return OperationRisk.FINANCIAL_ACTION
    if any(token in haystack for token in CREDENTIAL_TOKENS):
        return OperationRisk.CREDENTIAL_ACTION
    if any(token in haystack for token in ADMIN_TOKENS):
        return OperationRisk.ADMIN_ACTION
    if any(token in haystack for token in EXTERNAL_COMMUNICATION_TOKENS):
        return OperationRisk.EXTERNAL_COMMUNICATION
    if not side_effect and any(token in haystack for token in SENSITIVE_TOKENS):
        return OperationRisk.SENSITIVE_DATA_ACCESS
    if side_effect and idempotent:
        return OperationRisk.IDEMPOTENT_MUTATION
    if side_effect:
        return OperationRisk.REVERSIBLE_MUTATION
    return OperationRisk.READ_ONLY


def score_operation_contract(operation: Operation) -> dict[str, Any]:
    score = 100
    warnings: list[str] = []

    if len(operation.name) < 4 or operation.name in {"get", "post", "put", "delete"}:
        score -= 20
        warnings.append("Tool name is too generic.")
    if not operation.description or len(operation.description.strip()) < 24:
        score -= 20
        warnings.append("Description should explain the business purpose.")
    if not operation.input_schema or operation.input_schema.get("type") != "object":
        score -= 15
        warnings.append("Input schema should be an object schema.")
    if operation.side_effect and operation.risk == OperationRisk.REVERSIBLE_MUTATION:
        score -= 10
        warnings.append("Mutation risk is generic; add approval or reversibility metadata.")
    if operation.auth_requirements and operation.risk == OperationRisk.READ_ONLY:
        score -= 5
        warnings.append("Authenticated operation should document data sensitivity.")
    if operation.output_schema is None:
        score -= 10
        warnings.append("Output schema is not declared.")

    return {
        "score": max(score, 0),
        "warnings": warnings,
        "risk": operation.risk.value,
    }
