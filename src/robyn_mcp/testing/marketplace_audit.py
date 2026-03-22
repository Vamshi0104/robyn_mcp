
from __future__ import annotations

from pathlib import Path


def audit_marketplace_assets(project_root: str | Path) -> dict[str, object]:
    root = Path(project_root)
    vscode = root / 'extensions' / 'vscode'
    jetbrains = root / 'extensions' / 'jetbrains'
    docs = root / 'docs'
    checks = {
        'vscodeReady': (vscode / 'package.json').exists() and (vscode / '.vscodeignore').exists(),
        'jetbrainsReady': (jetbrains / 'build.gradle.kts').exists() and (jetbrains / 'README.md').exists(),
        'editorReleaseDoc': (docs / 'editor_release.md').exists(),
        'marketplaceDoc': (docs / 'marketplace_submission.md').exists(),
        'announcementDoc': (docs / 'release_announcement.md').exists(),
    }
    checks['ok'] = all(bool(v) for v in checks.values())
    return checks
