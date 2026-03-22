import json
import os
import subprocess
import sys
from pathlib import Path



def _subprocess_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src = str(project_root / 'src')
    existing = env.get('PYTHONPATH')
    env['PYTHONPATH'] = src if not existing else src + os.pathsep + existing
    return env

from robyn_mcp.testing.release_audit import audit_release_bundle


def test_release_audit_function():
    root = Path(__file__).resolve().parents[1]
    payload = audit_release_bundle(root)
    assert payload["ok"] is True
    assert payload["version"] == "1.0.0"
    assert payload["versionConsistent"] is True
    assert payload["missingPaths"] == []


def test_release_audit_cli_json():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "robyn_mcp.cli", "release-audit", "--project-root", str(root), "--json"],
        check=True,
        capture_output=True,
        text=True,
        env=_subprocess_env(root),
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["version"] == "1.0.0"


def test_release_bundle_points_to_final_docs():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "robyn_mcp.cli", "release-bundle", "--json"],
        check=True,
        capture_output=True,
        text=True,
        env=_subprocess_env(root),
    )
    payload = json.loads(result.stdout)
    assert payload["releaseNotes"].endswith("release_notes_v0_16_0.md")
    assert payload["launchChecklist"].endswith("final_release_checklist.md")
