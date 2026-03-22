from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


DEFAULT_SITE_FILES = [
    'website/index.html',
    'website/styles.css',
    'website/app.js',
    'docs/assets/launch_hero.svg',
    'docs/assets/jetbrains_toolwindow.svg',
    'docs/assets/benchmark_table.svg',
]


def export_static_site(project_root: str | Path, out_dir: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = Path(out_dir).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for rel in DEFAULT_SITE_FILES:
        source = root / rel
        if not source.exists():
            raise FileNotFoundError(f'Missing site asset: {source}')
        target_name = source.name if source.parent.name != 'website' else rel.split('/', 1)[1]
        target = out / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(str(target.relative_to(out)))
    return {
        'outputDir': str(out),
        'files': copied,
        'entrypoint': str((out / 'index.html').resolve()),
    }
