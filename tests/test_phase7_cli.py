
import json
import os
import subprocess
import sys
from pathlib import Path

from robyn_mcp.testing.announcement import build_announcement_bundle
from robyn_mcp.testing.marketplace_audit import audit_marketplace_assets


def _subprocess_env(project_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src = str(project_root / 'src')
    existing = env.get('PYTHONPATH')
    env['PYTHONPATH'] = src if not existing else src + os.pathsep + existing
    return env


def test_build_announcement_bundle(tmp_path):
    root = Path(__file__).resolve().parents[1]
    bundle = build_announcement_bundle(root, tmp_path / 'announcement')
    assert bundle.markdown_path.exists()
    assert bundle.social_card_path.exists()
    summary = json.loads(bundle.summary_path.read_text())
    assert summary['version'] == '1.0.0'


def test_build_announcement_cli_json(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, '-m', 'robyn_mcp.cli', 'build-announcement', '--project-root', str(root), '--out', str(tmp_path / 'announcement'), '--json'],
        check=True, capture_output=True, text=True, env=_subprocess_env(root)
    )
    payload = json.loads(result.stdout)
    assert payload['markdownPath'].endswith('announcement.md')


def test_marketplace_audit():
    root = Path(__file__).resolve().parents[1]
    payload = audit_marketplace_assets(root)
    assert payload['ok'] is True


def test_release_audit_reflects_phase17_assets():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, '-m', 'robyn_mcp.cli', 'release-audit', '--json'],
        check=True, capture_output=True, text=True, env=_subprocess_env(root)
    )
    payload = json.loads(result.stdout)
    assert payload['ok'] is True
    assert payload['marketplaceReady'] is True
    assert payload['version'] == '1.0.0'
