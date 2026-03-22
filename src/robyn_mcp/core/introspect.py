from __future__ import annotations

import copy
import inspect
from typing import Any

from robyn_mcp.core.config import RobynMCPConfig
from robyn_mcp.core.expose import ROB_MCP_META, ROB_MCP_PROMPT_META, ROB_MCP_RESOURCE_META
from robyn_mcp.core.models import PromptArgument, PromptDefinition, ResourceDefinition, RouteMetadata
from robyn_mcp.schemas.json_schema import signature_to_input_schema

_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _resolve_ref(schema: Any, components: dict[str, Any]) -> Any:
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        ref = str(schema["$ref"])
        if not ref.startswith("#/components/"):
            return schema
        node: Any = components
        for part in ref.removeprefix("#/components/").split("/"):
            if not isinstance(node, dict):
                return schema
            node = node.get(part)
        return _resolve_ref(copy.deepcopy(node), components)

    resolved = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            resolved[key] = _resolve_ref(value, components)
        elif isinstance(value, list):
            resolved[key] = [_resolve_ref(item, components) for item in value]
        else:
            resolved[key] = value
    return resolved


def _get_openapi_schema(app: Any) -> dict[str, Any]:
    candidates = []

    for attr in ("openapi", "openapi_schema", "_openapi_schema", "schema", "spec"):
        if hasattr(app, attr):
            candidates.append(getattr(app, attr))

    router = getattr(app, "router", None)
    if router is not None:
        for attr in ("openapi", "openapi_schema", "_openapi_schema", "schema", "spec"):
            if hasattr(router, attr):
                candidates.append(getattr(router, attr))

    for candidate in candidates:
        try:
            value = candidate() if callable(candidate) else candidate
            if isinstance(value, dict) and value.get("paths"):
                return value
        except Exception:
            continue

    return {}


def _build_openapi_index(app: Any, config: RobynMCPConfig) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    schema = _get_openapi_schema(app)
    if not schema:
        return {}, {}

    components = schema.get("components") or {}
    paths = schema.get("paths") or {}
    index: dict[tuple[str, str], dict[str, Any]] = {}

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, spec in methods.items():
            if not isinstance(spec, dict):
                continue
            method_l = str(method).lower()
            if method_l not in _HTTP_METHODS:
                continue
            index[(str(path), method_l)] = _resolve_ref(spec, components) if config.resolve_openapi_refs else spec

    return index, components


def _extract_examples(spec: dict[str, Any], config: RobynMCPConfig) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    request_body = spec.get("requestBody") or {}
    content = request_body.get("content") or {}
    ordered = list(config.prefer_openapi_body_content_types) + [k for k in content if k not in config.prefer_openapi_body_content_types]

    for content_type in ordered:
        entry = content.get(content_type)
        if not isinstance(entry, dict):
            continue

        raw_examples = entry.get("examples")
        if isinstance(raw_examples, dict):
            for name, item in raw_examples.items():
                if isinstance(item, dict) and item.get("value") is not None:
                    examples.append({"name": str(name), "arguments": item["value"], "contentType": content_type})

        if entry.get("example") is not None:
            examples.append({"name": "default", "arguments": entry["example"], "contentType": content_type})

        if examples:
            break

    return examples


def _extract_best_response_schema(spec: dict[str, Any], config: RobynMCPConfig) -> dict[str, Any] | None:
    responses = spec.get("responses") or {}
    for status_code in ("200", "201", "202", "204", "default"):
        response = responses.get(status_code) or {}
        content = response.get("content") or {}
        ordered = list(config.prefer_openapi_body_content_types) + [k for k in content if k not in config.prefer_openapi_body_content_types]
        for content_type in ordered:
            schema = (content.get(content_type) or {}).get("schema")
            if schema is not None:
                return schema
    return None


def _parameter_to_schema(param: dict[str, Any]) -> tuple[str, dict[str, Any], bool] | None:
    name = param.get("name")
    location = param.get("in")
    if not isinstance(name, str) or location not in {"path", "query", "header", "cookie"}:
        return None

    schema = copy.deepcopy(param.get("schema") or {"type": "string"})
    description = param.get("description")
    if description and isinstance(schema, dict):
        schema.setdefault("description", description)
    if isinstance(schema, dict):
        schema.setdefault("x-mcp-source", location)

    return name, schema, bool(param.get("required", False) or location == "path")


def _merge_request_schema(spec: dict[str, Any], handler: Any, config: RobynMCPConfig) -> dict[str, Any]:
    signature_schema = signature_to_input_schema(handler)
    properties = dict(signature_schema.get("properties", {}))
    required = set(signature_schema.get("required", []))

    for param in spec.get("parameters", []) or []:
        if not isinstance(param, dict):
            continue
        parsed = _parameter_to_schema(param)
        if parsed is None:
            continue
        name, schema, is_required = parsed
        if schema.get("x-mcp-source") == "header" and not config.include_header_parameters_in_schema:
            continue
        properties[name] = schema
        if is_required:
            required.add(name)

    request_body = spec.get("requestBody") or {}
    content = request_body.get("content") or {}
    ordered = list(config.prefer_openapi_body_content_types) + [k for k in content if k not in config.prefer_openapi_body_content_types]

    body_schema = None
    selected_type = None
    for content_type in ordered:
        item = content.get(content_type)
        if not isinstance(item, dict):
            continue
        if item.get("schema") is not None:
            body_schema = copy.deepcopy(item["schema"])
            selected_type = content_type
            break

    if body_schema is not None:
        if body_schema.get("type") == "object" and isinstance(body_schema.get("properties"), dict):
            for key, value in body_schema["properties"].items():
                if isinstance(value, dict):
                    properties[key] = value
            required.update(set(body_schema.get("required", [])))
        else:
            properties["body"] = body_schema
            if request_body.get("required"):
                required.add("body")

        if selected_type:
            body_props = body_schema.get("properties", {}) if isinstance(body_schema, dict) else {}
            for key, value in properties.items():
                if ((isinstance(value, dict) and key in body_props) or key == "body") and isinstance(value, dict):
                    value.setdefault("x-mcp-content-type", selected_type)

    merged: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        merged["required"] = sorted(required)
    return merged


def _iter_routes(app: Any) -> list[Any]:
    collected: list[Any] = []

    for container in (
        getattr(app, "routes", None),
        getattr(getattr(app, "router", None), "routes", None),
    ):
        if isinstance(container, list):
            collected.extend(container)
        elif isinstance(container, tuple):
            collected.extend(list(container))
        elif isinstance(container, dict):
            for v in container.values():
                if isinstance(v, list):
                    collected.extend(v)
                elif isinstance(v, tuple):
                    collected.extend(list(v))
                else:
                    collected.append(v)

    seen: set[int] = set()
    deduped: list[Any] = []
    for route in collected:
        rid = id(route)
        if rid in seen:
            continue
        seen.add(rid)
        deduped.append(route)

    return deduped


def _resolve_handler(route: Any) -> Any | None:
    for attr in ("handler", "endpoint", "function", "callable", "func", "f"):
        value = getattr(route, attr, None)
        if value is None:
            continue

        for inner_attr in ("handler", "endpoint", "function", "func", "callable", "f", "py_function"):
            inner = getattr(value, inner_attr, None)
            if inner is not None:
                value = inner
                break

        try:
            return inspect.unwrap(value)
        except Exception:
            return value
    return None


def _resolve_path(route: Any) -> str:
    for attr in ("route", "path", "uri", "endpoint_path", "rule"):
        value = getattr(route, attr, None)
        if value:
            return str(value)
    return ""


def _resolve_method(route: Any) -> str:
    for attr in ("route_type", "method", "http_method", "verb"):
        value = getattr(route, attr, None)
        if value:
            text = str(value).lower()
            if "." in text:
                text = text.split(".")[-1]
            return text
    return "get"


def _should_auto_expose_tool(path: str, method: str, spec: dict[str, Any], config: RobynMCPConfig) -> bool:
    if not config.auto_expose_openapi:
        return False

    if method == "get" and not config.auto_expose_safe_get_as_tools:
        return False
    if method in {"post", "put", "patch", "delete"} and not config.auto_expose_mutations_as_tools:
        return False

    operation_id = str(spec.get("operationId") or "").strip()
    tags = set(spec.get("tags", []) or [])

    if config.auto_expose_operation_allowlist and operation_id not in config.auto_expose_operation_allowlist:
        return False
    if config.auto_expose_operation_denylist and operation_id in config.auto_expose_operation_denylist:
        return False
    if config.auto_expose_tag_allowlist and not (tags & config.auto_expose_tag_allowlist):
        return False
    if config.auto_expose_tag_denylist and (tags & config.auto_expose_tag_denylist):
        return False

    return True


def _build_auto_tool_meta(handler: Any, method: str, spec: dict[str, Any], config: RobynMCPConfig) -> dict[str, Any]:
    operation_id = spec.get("operationId") or getattr(handler, "__name__", "tool")
    summary = spec.get("summary") or operation_id.replace("_", " ").title()
    description = spec.get("description") or config.auto_generated_description_suffix
    tags = list(spec.get("tags", []))
    side_effect = method in {"post", "put", "patch", "delete"}

    return {
        "operation_id": operation_id,
        "summary": summary,
        "description": description,
        "human_summary": None,
        "tags": tags,
        "requires_auth": False,
        "side_effect": side_effect,
        "idempotent": None,
        "auth_scopes": [],
        "required_permissions": [],
        "examples": _extract_examples(spec, config),
    }


def extract_routes(app: Any, config: RobynMCPConfig | None = None) -> list[RouteMetadata]:
    config = config or RobynMCPConfig()
    openapi_index, _components = _build_openapi_index(app, config)
    output: list[RouteMetadata] = []
    seen_keys: set[tuple[str, str]] = set()

    # first pass: concrete routes
    for route in _iter_routes(app):
        handler = _resolve_handler(route)
        if handler is None:
            continue

        path = _resolve_path(route)
        method = _resolve_method(route)
        seen_keys.add((path, method))
        spec = openapi_index.get((path, method), {})
        meta = getattr(handler, ROB_MCP_META, None)

        if meta:
            security = spec.get("security") or []
            scopes = sorted(
                {
                    scope
                    for item in security
                    if isinstance(item, dict)
                    for scope_list in item.values()
                    for scope in (scope_list or [])
                }
            )

            output.append(
                RouteMetadata(
                    path=path,
                    method=method,
                    handler=handler,
                    operation_id=meta.get("operation_id") or spec.get("operationId") or getattr(handler, "__name__", "tool"),
                    summary=meta.get("summary") or spec.get("summary"),
                    description=meta.get("description") or spec.get("description"),
                    human_summary=meta.get("human_summary"),
                    tags=list(meta.get("tags", spec.get("tags", []))),
                    requires_auth=bool(meta.get("requires_auth", False) or getattr(route, "auth_required", False) or bool(security)),
                    side_effect=bool(meta.get("side_effect", method in {"post", "put", "patch", "delete"})),
                    idempotent=meta.get("idempotent"),
                    exposed=bool(meta.get("exposed", True)),
                    auth_scopes=list(meta.get("auth_scopes", [])) or scopes,
                    required_permissions=list(meta.get("required_permissions", [])),
                    request_body_schema=_merge_request_schema(spec, handler, config) if spec else signature_to_input_schema(handler),
                    response_schema=_extract_best_response_schema(spec, config),
                    examples=list(meta.get("examples", [])) or _extract_examples(spec, config),
                    auto_generated=False,
                    source="decorator",
                    openapi_tags=list(spec.get("tags", [])),
                )
            )
            continue

        if config.auto_expose_openapi:
            if spec:
                if not _should_auto_expose_tool(path, method, spec, config):
                    continue
                auto_meta = _build_auto_tool_meta(handler, method, spec, config)
                request_schema = _merge_request_schema(spec, handler, config)
                response_schema = _extract_best_response_schema(spec, config)
                tags = list(spec.get("tags", []))
            else:
                if method == "get" and not config.auto_expose_safe_get_as_tools:
                    continue
                if method in {"post", "put", "patch", "delete"} and not config.auto_expose_mutations_as_tools:
                    continue

                operation_id = getattr(handler, "__name__", "tool")
                if config.auto_expose_operation_allowlist and operation_id not in config.auto_expose_operation_allowlist:
                    continue
                if config.auto_expose_operation_denylist and operation_id in config.auto_expose_operation_denylist:
                    continue

                auto_meta = {
                    "operation_id": operation_id,
                    "summary": operation_id.replace("_", " ").title(),
                    "description": config.auto_generated_description_suffix,
                    "human_summary": None,
                    "tags": [],
                    "requires_auth": False,
                    "side_effect": method in {"post", "put", "patch", "delete"},
                    "idempotent": None,
                    "auth_scopes": [],
                    "required_permissions": [],
                    "examples": [],
                }
                request_schema = signature_to_input_schema(handler)
                response_schema = None
                tags = []

            output.append(
                RouteMetadata(
                    path=path,
                    method=method,
                    handler=handler,
                    operation_id=auto_meta["operation_id"],
                    summary=auto_meta.get("summary"),
                    description=auto_meta.get("description"),
                    human_summary=auto_meta.get("human_summary"),
                    tags=list(auto_meta.get("tags", tags)),
                    requires_auth=bool(auto_meta.get("requires_auth", False)),
                    side_effect=bool(auto_meta.get("side_effect", False)),
                    idempotent=auto_meta.get("idempotent"),
                    exposed=True,
                    auth_scopes=list(auto_meta.get("auth_scopes", [])),
                    required_permissions=list(auto_meta.get("required_permissions", [])),
                    request_body_schema=request_schema,
                    response_schema=response_schema,
                    examples=list(auto_meta.get("examples", [])),
                    auto_generated=True,
                    source="openapi",
                    openapi_tags=tags,
                )
            )
            continue

        # default fallback: plain route exposure for legacy/test apps
        security = spec.get("security") or []
        scopes = sorted(
            {
                scope
                for item in security
                if isinstance(item, dict)
                for scope_list in item.values()
                for scope in (scope_list or [])
            }
        )

        operation_id = spec.get("operationId") or getattr(handler, "__name__", "tool")
        output.append(
            RouteMetadata(
                path=path,
                method=method,
                handler=handler,
                operation_id=operation_id,
                summary=spec.get("summary") or operation_id.replace("_", " ").title(),
                description=spec.get("description"),
                human_summary=None,
                tags=list(spec.get("tags", [])),
                requires_auth=bool(getattr(route, "auth_required", False) or bool(security)),
                side_effect=method in {"post", "put", "patch", "delete"},
                idempotent=None,
                exposed=True,
                auth_scopes=scopes,
                required_permissions=[],
                request_body_schema=_merge_request_schema(spec, handler, config) if spec else signature_to_input_schema(handler),
                response_schema=_extract_best_response_schema(spec, config) if spec else None,
                examples=_extract_examples(spec, config) if spec else [],
                auto_generated=bool(spec),
                source="openapi" if spec else "route",
                openapi_tags=list(spec.get("tags", [])),
            )
        )

    # second pass: pure OpenAPI fallback
    for (path, method), spec in openapi_index.items():
        if (path, method) in seen_keys:
            continue

        operation_id = str(spec.get("operationId") or "").strip()
        if not operation_id:
            operation_id = f"{method}_{path.strip('/').replace('/', '_') or 'root'}"

        synthetic_handler = (lambda **kwargs: kwargs)
        synthetic_handler.__name__ = operation_id

        if config.auto_expose_openapi:
            if not _should_auto_expose_tool(path, method, spec, config):
                continue
            auto_meta = _build_auto_tool_meta(synthetic_handler, method, spec, config)
            output.append(
                RouteMetadata(
                    path=path,
                    method=method,
                    handler=synthetic_handler,
                    operation_id=auto_meta["operation_id"],
                    summary=auto_meta.get("summary"),
                    description=auto_meta.get("description"),
                    human_summary=auto_meta.get("human_summary"),
                    tags=list(auto_meta.get("tags", spec.get("tags", []))),
                    requires_auth=bool(auto_meta.get("requires_auth", False)),
                    side_effect=bool(auto_meta.get("side_effect", method in {"post", "put", "patch", "delete"})),
                    idempotent=auto_meta.get("idempotent"),
                    exposed=True,
                    auth_scopes=list(auto_meta.get("auth_scopes", [])),
                    required_permissions=[],
                    request_body_schema=_merge_request_schema(spec, synthetic_handler, config),
                    response_schema=_extract_best_response_schema(spec, config),
                    examples=list(auto_meta.get("examples", [])) or _extract_examples(spec, config),
                    auto_generated=True,
                    source="openapi",
                    openapi_tags=list(spec.get("tags", [])),
                )
            )
        else:
            output.append(
                RouteMetadata(
                    path=path,
                    method=method,
                    handler=synthetic_handler,
                    operation_id=operation_id,
                    summary=spec.get("summary"),
                    description=spec.get("description"),
                    human_summary=None,
                    tags=list(spec.get("tags", [])),
                    requires_auth=bool(spec.get("security")),
                    side_effect=method in {"post", "put", "patch", "delete"},
                    idempotent=None,
                    exposed=True,
                    auth_scopes=sorted(
                        {
                            scope
                            for item in (spec.get("security") or [])
                            if isinstance(item, dict)
                            for scope_list in item.values()
                            for scope in (scope_list or [])
                        }
                    ),
                    required_permissions=[],
                    request_body_schema=_merge_request_schema(spec, synthetic_handler, config),
                    response_schema=_extract_best_response_schema(spec, config),
                    examples=_extract_examples(spec, config),
                    auto_generated=True,
                    source="openapi",
                    openapi_tags=list(spec.get("tags", [])),
                )
            )

    return output

def extract_resources(app: Any, config: RobynMCPConfig | None = None) -> list[ResourceDefinition]:
    config = config or RobynMCPConfig()
    items: list[ResourceDefinition] = []
    seen: set[int] = set()

    for route in _iter_routes(app):
        handler = _resolve_handler(route)
        if handler is None or id(handler) in seen:
            continue
        seen.add(id(handler))

        meta = getattr(handler, ROB_MCP_RESOURCE_META, None)
        if not meta:
            continue

        items.append(
            ResourceDefinition(
                uri=str(meta["uri"]),
                name=str(meta.get("name") or getattr(handler, "__name__", "resource")),
                handler=handler,
                description=meta.get("description"),
                mime_type=str(meta.get("mime_type") or "application/json"),
                tags=list(meta.get("tags", [])),
                requires_auth=bool(meta.get("requires_auth", False)),
                annotations=dict(meta.get("annotations", {})),
            )
        )

    return items


def _prompt_arguments_from_signature(handler: Any) -> list[PromptArgument]:
    signature = inspect.signature(handler)
    result: list[PromptArgument] = []
    for name, param in signature.parameters.items():
        if name == "request":
            continue
        result.append(PromptArgument(name=name, required=param.default is inspect.Signature.empty))
    return result


def extract_prompts(app: Any) -> list[PromptDefinition]:
    items: list[PromptDefinition] = []
    seen: set[int] = set()

    for route in _iter_routes(app):
        handler = _resolve_handler(route)
        if handler is None or id(handler) in seen:
            continue
        seen.add(id(handler))

        meta = getattr(handler, ROB_MCP_PROMPT_META, None)
        if not meta:
            continue

        args = [
            PromptArgument(
                name=str(arg["name"]),
                description=arg.get("description"),
                required=bool(arg.get("required", True)),
            )
            for arg in meta.get("arguments", [])
            if isinstance(arg, dict) and "name" in arg
        ] or _prompt_arguments_from_signature(handler)

        items.append(
            PromptDefinition(
                name=str(meta.get("name") or getattr(handler, "__name__", "prompt")),
                title=meta.get("title"),
                description=meta.get("description"),
                handler=handler,
                arguments=args,
                tags=list(meta.get("tags", [])),
                requires_auth=bool(meta.get("requires_auth", False)),
                annotations=dict(meta.get("annotations", {})),
            )
        )

    return items