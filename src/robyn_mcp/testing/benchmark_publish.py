from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def build_benchmark_markdown(robyn_path: str | Path, fastapi_path: str | Path) -> str:
    robyn = _load(robyn_path)
    fastapi = _load(fastapi_path)
    robyn_name = robyn.get("name", "robyn_mcp")
    fastapi_name = fastapi.get("name", "fastapi_mcp")
    rows = []
    metric_names = sorted(set((robyn.get("metrics") or {}).keys()) | set((fastapi.get("metrics") or {}).keys()))
    for name in metric_names:
        rv = (robyn.get("metrics") or {}).get(name)
        fv = (fastapi.get("metrics") or {}).get(name)
        delta = None
        if isinstance(rv, (int, float)) and isinstance(fv, (int, float)) and fv != 0:
            delta = ((rv - fv) / fv) * 100
        delta_text = f"{delta:.2f}%" if delta is not None else "n/a"
        rows.append(f"| {name} | {rv} | {fv} | {delta_text} |")

    env = robyn.get("environment") or {}
    return "\n".join([
        "# Benchmark comparison",
        "",
        f"- Candidate: **{robyn_name}**",
        f"- Baseline: **{fastapi_name}**",
        f"- Python: `{env.get('python', 'unknown')}`",
        f"- Platform: `{env.get('platform', 'unknown')}`",
        "",
        "| Metric | robyn_mcp | fastapi_mcp | Delta |",
        "|---|---:|---:|---:|",
        *rows,
        "",
        "> Lower latency is better; higher throughput is better. Validate methodology before publishing claims.",
    ]) + "\n"


def write_benchmark_markdown(robyn_path: str | Path, fastapi_path: str | Path, out_path: str | Path) -> str:
    content = build_benchmark_markdown(robyn_path, fastapi_path)
    out = Path(out_path)
    out.write_text(content)
    return str(out)
