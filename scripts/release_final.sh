#!/usr/bin/env bash
set -euo pipefail

python -m pytest
python -m robyn_mcp.cli release-audit --json
python -m build
python -m twine check dist/*
echo "Phase 15 final-release checks completed."
