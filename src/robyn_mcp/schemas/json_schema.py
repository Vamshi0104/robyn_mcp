from __future__ import annotations

import enum
import inspect
from dataclasses import MISSING, fields, is_dataclass
from typing import Any, Literal, TypedDict, get_args, get_origin, get_type_hints


_SIMPLE = {str: "string", int: "integer", float: "number", bool: "boolean"}


def _typed_dict_schema(annotation: Any) -> dict[str, Any]:
    hints = getattr(annotation, "__annotations__", {})
    required_keys = set(getattr(annotation, "__required_keys__", set(hints.keys())))
    properties = {name: annotation_to_schema(hint) for name, hint in hints.items()}
    schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required_keys:
        schema["required"] = sorted(required_keys)
    return schema


def _object_schema_from_signature(annotation: Any) -> dict[str, Any]:
    try:
        signature = inspect.signature(annotation)
    except (TypeError, ValueError):
        return {"type": "object", "additionalProperties": True}
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        properties[name] = annotation_to_schema(param.annotation)
        if param.default is inspect.Signature.empty:
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema


def annotation_to_schema(annotation: Any) -> dict[str, Any]:
    if annotation is inspect.Signature.empty or annotation is Any:
        return {"type": "string"}
    if annotation in _SIMPLE:
        return {"type": _SIMPLE[annotation]}

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (list, tuple, set):
        item_schema = annotation_to_schema(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": item_schema}

    if origin is dict:
        key_schema = annotation_to_schema(args[0]) if len(args) >= 1 else {"type": "string"}
        value_schema = annotation_to_schema(args[1]) if len(args) >= 2 else {"type": "string"}
        schema: dict[str, Any] = {"type": "object", "additionalProperties": value_schema}
        if key_schema.get("type") not in {None, "string"}:
            schema["propertyNames"] = key_schema
        return schema

    if origin is Literal:
        literals = list(args)
        if not literals:
            return {"type": "string"}
        if all(isinstance(item, str) for item in literals):
            return {"type": "string", "enum": literals}
        if all(isinstance(item, int) and not isinstance(item, bool) for item in literals):
            return {"type": "integer", "enum": literals}
        return {"enum": literals}

    if str(origin) == "typing.Union" and args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            schema = annotation_to_schema(non_none[0])
            schema["nullable"] = True
            return schema
        return {"anyOf": [annotation_to_schema(arg) for arg in non_none]}

    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        values = [item.value for item in annotation]
        if all(isinstance(item, str) for item in values):
            return {"type": "string", "enum": values}
        if all(isinstance(item, int) for item in values):
            return {"type": "integer", "enum": values}
        return {"enum": values}

    if hasattr(annotation, "model_json_schema"):
        return annotation.model_json_schema()

    if isinstance(annotation, type) and is_dataclass(annotation):
        properties: dict[str, Any] = {}
        required: list[str] = []
        type_hints = get_type_hints(annotation)
        for field in fields(annotation):
            field_annotation = type_hints.get(field.name, field.type)
            properties[field.name] = annotation_to_schema(field_annotation)
            if field.default is MISSING and field.default_factory is MISSING:
                required.append(field.name)
        schema = {"type": "object", "properties": properties, "additionalProperties": False}
        if required:
            schema["required"] = required
        return schema

    if isinstance(annotation, type) and hasattr(annotation, "__annotations__") and hasattr(annotation, "__required_keys__"):
        return _typed_dict_schema(annotation)

    if inspect.isclass(annotation) and getattr(annotation, "__annotations__", None):
        return _object_schema_from_signature(annotation)

    return {"type": "string"}


def signature_to_input_schema(handler: Any) -> dict[str, Any]:
    signature = inspect.signature(handler)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, param in signature.parameters.items():
        if name == "request":
            continue
        properties[name] = annotation_to_schema(param.annotation)
        if param.default is inspect.Signature.empty:
            required.append(name)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema
