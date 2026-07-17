## Summary

Describe the change and why it matters.

## Verification

- [ ] `python -m ruff check src tests examples/*.py`
- [ ] `pytest`
- [ ] `python -m robyn_mcp.cli release-audit --json`
- [ ] `python -m build`
- [ ] `python -m twine check dist/*`

## Compatibility

- [ ] No public compatibility claim was upgraded to `Verified` without evidence.
- [ ] Docs and changelog were updated when user-facing behavior changed.
- [ ] Security defaults, header forwarding, and approval metadata were considered.
