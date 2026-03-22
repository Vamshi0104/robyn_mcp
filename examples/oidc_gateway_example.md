# OIDC gateway example

1. Validate bearer tokens at the gateway or service mesh.
2. Forward only allowlisted identity fields into Robyn.
3. Configure `RobynMCPConfig` to read principal, tenant, client, and scopes from claims or headers.
4. Use scoped policy enforcement for high-risk tools.
