# Contributing

Thanks for contributing to `robyn-mcp`.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev,docs]
```

## Common commands

Run tests:

```bash
pytest
```

Run lint:

```bash
ruff check .
```

Build docs:

```bash
mkdocs build --strict
```

Build package artifacts:

```bash
python -m build
```

## Before opening a PR

Please make sure you have:
- run the test suite
- run lint checks
- updated docs or examples when behavior changed
- added tests for user-facing fixes when practical

## Development guidance

- Keep defaults safe for production use.
- Prefer explicit opt-in for resource, prompt, and OpenAPI auto-exposure features.
- Maintain compatibility with the documented MCP HTTP flow: metadata, initialize, tools, resources, prompts, and session lifecycle.
- Preserve user-facing setup simplicity: a clean `pip install robyn-mcp robyn` path should work on a fresh machine.
