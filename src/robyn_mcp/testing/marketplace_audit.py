from __future__ import annotations

from pathlib import Path


def audit_marketplace_assets(project_root: str | Path) -> dict[str, object]:
    root = Path(project_root)
    docs = root / "docs"
    has_vscode = (root / "extensions" / "vscode").exists()
    has_jetbrains = (root / "extensions" / "jetbrains").exists()
    checks = {
        "vscodeReady": True,
        "jetbrainsReady": True,
        "releaseGuide": (docs / "release.md").exists(),
        "readme": (root / "README.md").exists(),
        "website": (root / "index.html").exists(),
    }
    if has_vscode:
        vscode = root / "extensions" / "vscode"
        checks["vscodeReady"] = (vscode / "package.json").exists() and (
            vscode / ".vscodeignore"
        ).exists()
    if has_jetbrains:
        jetbrains = root / "extensions" / "jetbrains"
        checks["jetbrainsReady"] = (jetbrains / "build.gradle.kts").exists() and (
            jetbrains / "README.md"
        ).exists()
    checks["ok"] = all(bool(v) for v in checks.values())
    return checks
