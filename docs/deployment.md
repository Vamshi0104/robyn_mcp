# Deployment

## Reverse proxy posture

Recommended production edge:

- TLS termination at ingress / reverse proxy
- OIDC or JWT verification at the edge
- only forward explicitly allowlisted identity headers into `robyn_mcp`
- keep HTTP as the primary MCP transport
- enable SSE only when you need streaming server messages

## Forward only what you need

Typical safe forwarded headers:

- `authorization`
- `x-request-id`
- `x-correlation-id`
- `x-auth-sub`
- `x-tenant-id`
- `x-client-id`
- `x-auth-scopes`

## Kubernetes

Use a normal stateless deployment for the MCP server and keep session TTL reasonably short. Put rate limiting and auth at both the edge and application layers for defense in depth.

## OIDC/JWT

A practical pattern is: verify tokens at the gateway, map claims into allowlisted headers, then let `robyn_mcp` resolve principal / tenant / scopes from those headers and request claims.
