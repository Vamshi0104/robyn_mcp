from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tomllib

REQUIRED_DOCS = {
    "readme": "README.md",
    "changelog": "CHANGELOG.md",
    "license": "LICENSE",
    "docs_index": "docs/index.md",
    "docs_quickstart": "docs/quickstart.md",
    "docs_examples": "docs/examples.md",
    "docs_openapi": "docs/openapi_gateway.md",
    "docs_compatibility": "docs/compatibility.md",
    "docs_security": "docs/security.md",
    "docs_deployment": "docs/deployment.md",
    "docs_release": "docs/release.md",
    "docs_demo_asset": "docs/assets/demo_terminal.svg",
    "site_index": "index.html",
    "site_image": "assets/images/robyn_mcp.png",
    "release_script": "scripts/release_final.sh",
    "editor_script": "scripts/build_editor_artifacts.sh",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _read_python_version(init_path: Path) -> str:
    for line in init_path.read_text().splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError(f"__version__ not found in {init_path}")


def audit_release_bundle(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    pyproject = tomllib.loads((root / "pyproject.toml").read_text())
    pyproject_version = pyproject["project"]["version"]
    package_version = _read_python_version(root / "src" / "robyn_mcp" / "__init__.py")

    required_paths = {name: root / rel for name, rel in REQUIRED_DOCS.items()}
    missing = [name for name, path in required_paths.items() if not path.exists()]

    versions = {
        "pyproject": pyproject_version,
        "python_package": package_version,
    }
    consistency = len(set(versions.values())) == 1
    website_ready = all(
        (root / rel).exists() for rel in ["index.html", "assets/images/robyn_mcp.png"]
    )
    marketplace_ready = (root / "docs" / "release.md").exists()
    ok = consistency and not missing and website_ready and marketplace_ready

    return {
        "ok": ok,
        "version": pyproject_version,
        "versions": versions,
        "versionConsistent": consistency,
        "websiteReady": website_ready,
        "marketplaceReady": marketplace_ready,
        "requiredPaths": {name: str(path) for name, path in required_paths.items()},
        "missingPaths": missing,
        "summary": "release-ready" if ok else "release-audit-failed",
    }
