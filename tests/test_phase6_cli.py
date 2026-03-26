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

from robyn_mcp.testing.launch_bundle import build_launch_bundle
from robyn_mcp.testing.site_export import export_static_site


def test_build_launch_bundle_function(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = build_launch_bundle(root, tmp_path / 'bundle')
    assert result.file_count >= 10
    manifest = json.loads(result.manifest_path.read_text())
    checksums = json.loads(result.checksums_path.read_text())
    assert any(item['target'] == 'website/index.html' for item in manifest['files'])
    assert 'website/index.html' in checksums


def test_build_launch_bundle_cli_json(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'robyn_mcp.cli',
            'build-launch-bundle',
            '--project-root',
            str(root),
            '--out',
            str(tmp_path / 'bundle'),
            '--json',
        ],
        check=True,
        capture_output=True,
        text=True,
        env=_subprocess_env(root),
    )
    payload = json.loads(result.stdout)
    assert payload['fileCount'] >= 10
    assert payload['manifestPath'].endswith('launch_manifest.json')


def test_export_site_function(tmp_path):
    root = Path(__file__).resolve().parents[1]
    payload = export_static_site(root, tmp_path / 'site')
    assert Path(payload['entrypoint']).exists()
    assert 'index.html' in payload['files']


def test_release_audit_reflects_phase16_assets():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, '-m', 'robyn_mcp.cli', 'release-audit', '--json'],
        check=True,
        capture_output=True,
        text=True,
        env=_subprocess_env(root),
    )
    payload = json.loads(result.stdout)
    assert payload['ok'] is True
    assert payload['websiteReady'] is True
    assert payload['version'] == '1.0.1'
