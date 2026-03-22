from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def _load(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, dict):
        raise ValueError('benchmark payload must be a JSON object')
    return payload


def compare_benchmarks(robyn_path: str | Path, fastapi_path: str | Path) -> dict[str, Any]:
    robyn = _load(robyn_path)
    fastapi = _load(fastapi_path)
    robyn_latency = float(robyn.get('p50_ms', 0.0))
    fastapi_latency = float(fastapi.get('p50_ms', 0.0))
    robyn_rps = float(robyn.get('rps', 0.0))
    fastapi_rps = float(fastapi.get('rps', 0.0))
    summary = {
        'robyn_mcp': robyn,
        'fastapi_mcp': fastapi,
        'latency_delta_ms': round(robyn_latency - fastapi_latency, 3),
        'throughput_delta_rps': round(robyn_rps - fastapi_rps, 3),
        'winner_latency': 'robyn_mcp' if robyn_latency <= fastapi_latency else 'fastapi_mcp',
        'winner_throughput': 'robyn_mcp' if robyn_rps >= fastapi_rps else 'fastapi_mcp',
        'headline': f"Latency: {'robyn_mcp' if robyn_latency <= fastapi_latency else 'fastapi_mcp'}, Throughput: {'robyn_mcp' if robyn_rps >= fastapi_rps else 'fastapi_mcp'}",
    }
    return summary
