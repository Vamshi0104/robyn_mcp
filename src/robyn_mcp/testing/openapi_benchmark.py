from __future__ import annotations

import statistics
import time
from pathlib import Path
from typing import Any

from robyn_mcp.core.openapi_source import (
    OpenAPIOperationSource,
    analyze_operations,
    load_openapi_document,
)


def benchmark_openapi_inspection(source: str | Path, *, iterations: int = 10) -> dict[str, Any]:
    if iterations <= 0:
        raise ValueError("iterations must be > 0")

    document = load_openapi_document(source)
    durations_ms: list[float] = []
    operation_count = 0
    last_report: dict[str, Any] | None = None

    for _ in range(iterations):
        started = time.perf_counter()
        operations = OpenAPIOperationSource(document).discover()
        report = analyze_operations(operations).as_dict()
        durations_ms.append((time.perf_counter() - started) * 1000.0)
        operation_count = len(operations)
        last_report = report

    return {
        "source": str(source),
        "iterations": iterations,
        "operationCount": operation_count,
        "minMs": round(min(durations_ms), 4),
        "meanMs": round(statistics.mean(durations_ms), 4),
        "medianMs": round(statistics.median(durations_ms), 4),
        "maxMs": round(max(durations_ms), 4),
        "lastReport": last_report,
    }
