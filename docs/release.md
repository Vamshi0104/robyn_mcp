# Release

This page consolidates the release, verification, demo, and launch checklist for `robyn-mcp`.

## Version

The prepared release version is `1.0.4`.

Before publishing:

```bash
python -m ruff check src tests examples/*.py
pytest
python -m robyn_mcp.cli release-audit --json
python -m build
python -m twine check dist/*
```

## Package Flow

Build clean artifacts:

```bash
rm -rf dist build src/robyn_mcp.egg-info
python -m build
python -m twine check dist/*
```

Verify the package with TestPyPI or Trusted Publishing before production PyPI. Keep credentials out of the repository and shell history where possible.

Production upload:

```bash
python -m twine upload dist/*
```

## Clean Install Verification

Use a fresh environment after upload:

```bash
python -m venv /tmp/robyn-mcp-release-check
/tmp/robyn-mcp-release-check/bin/python -m pip install --upgrade pip
/tmp/robyn-mcp-release-check/bin/python -m pip install robyn robyn-mcp==1.0.4
/tmp/robyn-mcp-release-check/bin/robyn-mcp runtime --json
```

## GitHub Release

Suggested title:

```text
robyn-mcp 1.0.4
```

Suggested highlights:

- OpenAPI operation inspection with local `$ref` resolution.
- OpenAPI gateway invocation for controlled upstream tests.
- FastAPI operation source through `app.openapi()`.
- `robyn-mcp doctor` endpoint checks.
- `robyn-mcp benchmark-openapi` inspection timing.
- Risk metadata, approval annotations, and contract-quality scoring.

Tag:

```bash
git tag v1.0.4
git push origin v1.0.4
```

## Demo Recording

Record the customer-support flow and replace the README static preview with `docs/assets/robyn_mcp_demo.gif`.

Recommended flow:

1. Start `python examples/customer_support_app.py`.
2. Open `http://localhost:8080/mcp/playground`.
3. Show initialize, `tools/list`, risk metadata, and `get_customer`.
4. Run `robyn-mcp doctor http://localhost:8080/mcp --json`.
5. Run `robyn-mcp inspect-openapi examples/openapi.json --json`.
6. Start `python examples/openapi_demo_server.py`.
7. Run `robyn-mcp invoke-openapi examples/openapi.json --upstream http://127.0.0.1:8098 --operation get_customer --args '{"customer_id":"cus_123","expand":"orders"}' --json`.

Keep the clip short, hide secrets, and export both `.gif` and `.mp4` when possible.

## Client Verification

Only mark a client as verified after recording:

- client name and version
- `robyn-mcp` version
- Python version
- transport
- exact setup steps
- pass/fail result
- date

Minimum smoke scenario:

1. Run `robyn-mcp doctor`.
2. Confirm `tools/list`.
3. Call one read-only tool.
4. Inspect one risky operation and confirm risk metadata.

## Community Launch

After PyPI and GitHub releases are live:

- Confirm `pip install robyn-mcp==1.0.4` works in a clean environment.
- Confirm docs are live at `https://vamshi0104.github.io/robyn_mcp/`.
- Attach or link the demo GIF/video.
- Share one concise technical post with real commands.
- Invite client compatibility reports through the issue template.
