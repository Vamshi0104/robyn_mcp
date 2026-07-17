# Governance

`robyn-mcp` is maintained as an open source MCP adapter and the reference implementation for a broader API-to-MCP direction.

## Maintainer Responsibilities

- Keep releases reproducible.
- Review protocol, security, and packaging changes carefully.
- Prefer compatibility over surprise behavior.
- Document breaking changes before release.
- Keep token, credential, and release-secret handling out of the repository.

## Decision Making

Small changes can be merged after maintainer review. Large changes should start as an issue or design note, especially changes to protocol behavior, security defaults, adapter contracts, or public APIs.

## Compatibility

Compatibility claims should be backed by repeatable tests, documented manual test steps, or CI evidence. Unverified client support should remain marked as planned or contract-level.

## Security

Security reports should follow `SECURITY.md`. Security fixes may be prepared privately before a public release note is published.
