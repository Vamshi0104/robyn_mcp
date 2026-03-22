from __future__ import annotations

import json
from pathlib import Path

from robyn_mcp.cli import main
from robyn_mcp.testing.benchmark_publish import build_benchmark_markdown


def test_build_benchmark_markdown(tmp_path: Path) -> None:
    robyn = tmp_path / "robyn.json"
    fastapi = tmp_path / "fastapi.json"
    robyn.write_text(json.dumps({"name": "robyn_mcp", "metrics": {"p95_ms": 11.0}, "environment": {"python": "3.12", "platform": "linux"}}))
    fastapi.write_text(json.dumps({"name": "fastapi_mcp", "metrics": {"p95_ms": 13.0}, "environment": {"python": "3.12", "platform": "linux"}}))
    content = build_benchmark_markdown(robyn, fastapi)
    assert "Benchmark comparison" in content
    assert "p95_ms" in content


def test_publish_benchmarks_cli(tmp_path: Path) -> None:
    robyn = tmp_path / "robyn.json"
    fastapi = tmp_path / "fastapi.json"
    out = tmp_path / "report.md"
    robyn.write_text(json.dumps({"metrics": {"latency_ms": 10.0}, "environment": {"python": "3.12", "platform": "linux"}}))
    fastapi.write_text(json.dumps({"metrics": {"latency_ms": 12.0}, "environment": {"python": "3.12", "platform": "linux"}}))
    assert main(["publish-benchmarks", str(robyn), str(fastapi), "--out", str(out)]) == 0
    assert out.exists()
    assert "latency_ms" in out.read_text()


def test_release_bundle_phase14_json(capsys) -> None:
    assert main(["release-bundle", "--json"]) == 0
    out = capsys.readouterr().out
    assert "release_candidate_checklist" not in out.lower() or "launchChecklist" in out
    assert "benchmark_publishing" not in out.lower() or "benchmarkPublishing" in out
