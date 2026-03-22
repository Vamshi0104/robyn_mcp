from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any


REQUIRED_DOCS = {
    'readme': 'README.md',
    'changelog': 'CHANGELOG.md',
    'license': 'LICENSE',
    'release_notes': 'docs/release_notes_v0_17_0.md',
    'release_checklist': 'docs/final_release_checklist.md',
    'launch_doc': 'docs/public_launch.md',
    'launch_bundle_doc': 'docs/launch_bundle.md',
    'editor_release_doc': 'docs/editor_release.md',
    'post_release_doc': 'docs/post_release_operations.md',
    'release_announcement_doc': 'docs/release_announcement.md',
    'marketplace_doc': 'docs/marketplace_submission.md',
    'website_index': 'website/index.html',
    'website_styles': 'website/styles.css',
    'website_app': 'website/app.js',
    'vscode_package': 'extensions/vscode/package.json',
    'jetbrains_plugin': 'extensions/jetbrains/src/main/resources/META-INF/plugin.xml',
    'release_script': 'scripts/release_final.sh',
    'editor_script': 'scripts/build_editor_artifacts.sh',
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _read_python_version(init_path: Path) -> str:
    for line in init_path.read_text().splitlines():
        if line.startswith('__version__'):
            return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise ValueError(f'__version__ not found in {init_path}')


def audit_release_bundle(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    pyproject = tomllib.loads((root / 'pyproject.toml').read_text())
    package_json = _load_json(root / 'extensions' / 'vscode' / 'package.json')
    pyproject_version = pyproject['project']['version']
    package_version = _read_python_version(root / 'src' / 'robyn_mcp' / '__init__.py')
    vscode_version = package_json['version']

    required_paths = {name: root / rel for name, rel in REQUIRED_DOCS.items()}
    missing = [name for name, path in required_paths.items() if not path.exists()]

    versions = {
        'pyproject': pyproject_version,
        'python_package': package_version,
        'vscode_extension': vscode_version,
    }
    consistency = len(set(versions.values())) == 1
    website_ready = all((root / rel).exists() for rel in ['website/index.html', 'website/styles.css', 'website/app.js'])
    marketplace_ready = all((root / rel).exists() for rel in ['docs/release_announcement.md', 'docs/marketplace_submission.md'])
    ok = consistency and not missing and website_ready and marketplace_ready

    return {
        'ok': ok,
        'version': pyproject_version,
        'versions': versions,
        'versionConsistent': consistency,
        'websiteReady': website_ready,
        'marketplaceReady': marketplace_ready,
        'requiredPaths': {name: str(path) for name, path in required_paths.items()},
        'missingPaths': missing,
        'summary': 'release-ready' if ok else 'release-audit-failed',
    }
