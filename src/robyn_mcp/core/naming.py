from __future__ import annotations

import re


_NON_ALNUM = re.compile(r"[^a-zA-Z0-9_]+")


def slugify_operation(value: str) -> str:
    value = value.strip().replace("-", "_").replace("/", "_")
    value = _NON_ALNUM.sub("_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "tool"


def unique_name(base: str, seen: set[str]) -> str:
    if base not in seen:
        seen.add(base)
        return base
    idx = 2
    while True:
        candidate = f"{base}_{idx}"
        if candidate not in seen:
            seen.add(candidate)
            return candidate
        idx += 1
