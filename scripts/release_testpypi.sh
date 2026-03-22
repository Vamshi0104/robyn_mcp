#!/usr/bin/env bash
set -euo pipefail
python -m pip install -U build twine
python -m build
python scripts/check_release_assets.py
twine check dist/*
echo "Ready for TestPyPI upload: python -m twine upload --repository testpypi dist/*"
