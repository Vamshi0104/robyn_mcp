from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_BUNDLE_FILES = {
    'README.md': 'README.md',
    'CHANGELOG.md': 'CHANGELOG.md',
    'LICENSE': 'LICENSE',
    'docs/release_notes_v0_16_0.md': 'docs/release_notes_v0_16_0.md',
    'docs/final_release_checklist.md': 'docs/final_release_checklist.md',
    'docs/public_launch.md': 'docs/public_launch.md',
    'docs/launch_bundle.md': 'docs/launch_bundle.md',
    'docs/editor_release.md': 'docs/editor_release.md',
    'docs/post_release_operations.md': 'docs/post_release_operations.md',
    'docs/assets/launch_hero.svg': 'docs/assets/launch_hero.svg',
    'docs/assets/jetbrains_toolwindow.svg': 'docs/assets/jetbrains_toolwindow.svg',
    'website/index.html': 'website/index.html',
    'website/styles.css': 'website/styles.css',
    'website/app.js': 'website/app.js',
    'extensions/vscode/package.json': 'extensions/vscode/package.json',
    'extensions/jetbrains/src/main/resources/META-INF/plugin.xml': 'extensions/jetbrains/src/main/resources/META-INF/plugin.xml',
    'scripts/release_final.sh': 'scripts/release_final.sh',
    'scripts/build_editor_artifacts.sh': 'scripts/build_editor_artifacts.sh',
}


@dataclass(slots=True)
class LaunchBundleResult:
    output_dir: Path
    manifest_path: Path
    checksums_path: Path
    file_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            'outputDir': str(self.output_dir),
            'manifestPath': str(self.manifest_path),
            'checksumsPath': str(self.checksums_path),
            'fileCount': self.file_count,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def build_launch_bundle(project_root: str | Path, out_dir: str | Path) -> LaunchBundleResult:
    root = Path(project_root).resolve()
    out = Path(out_dir).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []
    checksums: dict[str, str] = {}

    for source_rel, target_rel in DEFAULT_BUNDLE_FILES.items():
        source = root / source_rel
        if not source.exists():
            raise FileNotFoundError(f'Missing release asset: {source}')
        target = out / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        checksum = _sha256(target)
        entry = {
            'source': source_rel,
            'target': target_rel,
            'bytes': target.stat().st_size,
            'sha256': checksum,
        }
        manifest.append(entry)
        checksums[target_rel] = checksum

    manifest_path = out / 'launch_manifest.json'
    checksums_path = out / 'SHA256SUMS.json'
    manifest_path.write_text(json.dumps({'files': manifest}, indent=2))
    checksums_path.write_text(json.dumps(checksums, indent=2, sort_keys=True))
    return LaunchBundleResult(out, manifest_path, checksums_path, len(manifest))
