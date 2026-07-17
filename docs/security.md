# Security

Security-sensitive defaults in `robyn_mcp` should remain conservative:

- forward only explicitly allowlisted headers
- keep cookies blocked by default unless allowed
- validate origin where your deployment expects browser access
- keep human approval in the client/UI for sensitive tools
- rate-limit expensive or risky operations
- capture enough audit detail to explain what happened without leaking secrets
