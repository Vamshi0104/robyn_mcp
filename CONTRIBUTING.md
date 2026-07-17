# Contributing

Thanks for helping improve `robyn-mcp`. The best contributions make existing APIs safer and easier to expose through MCP.

## Good First Contributions

- Add a repeatable client verification report.
- Improve examples with real app flows.
- Add OpenAPI edge-case fixtures.
- Improve docs for installation, deployment, auth, or policy.
- Add tests for protocol behavior, gateway invocation, or schema generation.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Verify Before Opening a PR

```bash
python -m ruff check src tests examples/*.py
pytest
python -m robyn_mcp.cli release-audit --json
python -m build
python -m twine check dist/*
```

## Compatibility Claims

Do not mark a client as `Verified` unless you have a repeatable test record with:

- client name and version
- `robyn-mcp` version
- Python version
- transport
- exact setup steps
- result and date

Use the client verification issue template when reporting compatibility results.

## Security Defaults

Keep security behavior explicit:

- Do not forward all headers by default.
- Do not forward cookies unless configured.
- Keep risky operations marked with risk and approval metadata.
- Add tests for auth, policy, origin, or header-forwarding changes.
