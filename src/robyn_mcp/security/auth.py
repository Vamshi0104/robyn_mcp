
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from robyn_mcp.core.config import RobynMCPConfig


@dataclass(slots=True)
class AuthContext:
    principal: Any = None
    principal_id: str | None = None
    tenant_id: str | None = None
    client_id: str | None = None
    scopes: set[str] = field(default_factory=set)
    claims: dict[str, Any] = field(default_factory=dict)


class PrincipalResolver:
    def resolve(self, request: Any, headers: dict[str, str], config: RobynMCPConfig) -> AuthContext:
        return AuthContext()


def _as_dict_like(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items()}
    if value is None:
        return {}
    out: dict[str, Any] = {}
    for name in dir(value):
        if name.startswith('_'):
            continue
        try:
            item = getattr(value, name)
        except Exception:
            continue
        if callable(item):
            continue
        out[str(name)] = item
    return out


def _first_present(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ''):
            return mapping[key]
    return None


def _extract_scopes(claims: dict[str, Any], headers: dict[str, str], config: RobynMCPConfig) -> set[str]:
    scopes: set[str] = set()
    for header_name in config.scopes_header_names:
        raw = headers.get(header_name.lower())
        if raw:
            scopes.update({item.strip() for item in str(raw).replace(',', ' ').split() if item.strip()})
    claim_value = _first_present(claims, config.scope_claim_keys)
    if isinstance(claim_value, str):
        scopes.update({item.strip() for item in claim_value.replace(',', ' ').split() if item.strip()})
    elif isinstance(claim_value, (list, tuple, set)):
        scopes.update({str(item).strip() for item in claim_value if str(item).strip()})
    return scopes


class HeaderPrincipalResolver(PrincipalResolver):
    def resolve(self, request: Any, headers: dict[str, str], config: RobynMCPConfig) -> AuthContext:
        principal = getattr(request, 'identity', None)
        claims = _as_dict_like(getattr(request, 'claims', None))
        if not claims and principal is not None:
            claims = _as_dict_like(principal)

        principal_id = _first_present(claims, config.principal_claim_keys)
        if principal_id is None and principal is not None:
            principal_id = getattr(principal, 'sub', None) or getattr(principal, 'id', None) or str(principal)
        if principal_id is None and config.principal_header:
            principal_id = headers.get(config.principal_header.lower())

        tenant_id = _first_present(claims, config.tenant_claim_keys)
        if tenant_id is None and principal is not None:
            tenant_id = _first_present(_as_dict_like(principal), config.tenant_claim_keys)
        if tenant_id is None and config.tenant_header:
            tenant_id = headers.get(config.tenant_header.lower())

        client_id = _first_present(claims, config.client_claim_keys)
        if client_id is None and config.client_id_header:
            client_id = headers.get(config.client_id_header.lower())

        scopes = _extract_scopes(claims, headers, config)

        return AuthContext(
            principal=principal,
            principal_id=None if principal_id is None else str(principal_id),
            tenant_id=None if tenant_id is None else str(tenant_id),
            client_id=None if client_id is None else str(client_id),
            scopes=scopes,
            claims=claims,
        )
