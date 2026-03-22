from __future__ import annotations

import json
from pathlib import Path

from robyn_mcp.cli import main
from robyn_mcp.testing.benchmark_compare import compare_benchmarks


def test_compare_benchmarks(tmp_path, capsys):
    robyn = tmp_path / "robyn.json"
    fastapi = tmp_path / "fastapi.json"
    robyn.write_text(json.dumps({"p50_ms": 2.5, "rps": 900}))
    fastapi.write_text(json.dumps({"p50_ms": 3.0, "rps": 850}))
    rc = main(["compare-benchmarks", str(robyn), str(fastapi), "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["winner_latency"] == "robyn_mcp"
    assert out["winner_throughput"] == "robyn_mcp"


def test_release_bundle(capsys):
    rc = main(["release-bundle", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["releaseNotes"].endswith(("release_notes_v0_13_0.md", "release_notes_v0_14_0_rc1.md", "release_notes_v0_14_0.md", "release_notes_v0_16_0.md"))


def test_compare_benchmarks_helper(tmp_path):
    robyn = tmp_path / "robyn.json"
    fastapi = tmp_path / "fastapi.json"
    robyn.write_text(json.dumps({"p50_ms": 3.1, "rps": 700}))
    fastapi.write_text(json.dumps({"p50_ms": 2.8, "rps": 690}))
    summary = compare_benchmarks(robyn, fastapi)
    assert summary["winner_latency"] == "fastapi_mcp"
    assert summary["winner_throughput"] == "robyn_mcp"
