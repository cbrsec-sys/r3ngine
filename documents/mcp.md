# MCP Access

r3ngine exposes a dedicated `/api/mcp/` allowlist so IDE agents can read recon data and queue allowed jobs. The TypeScript server lives in `r3ngine-mcp/` (same layout as `r3ngine-mobile` and `r3ngine-plugins`). It never receives Postgres, Redis, Neo4j, or scan-result credentials.

## Generate a key

1. Open **Settings → MCP Access**.
2. Sys-admins set transport: **stdio**, **HTTP**, or **both**.
3. Generate a named key. Copy the secret (`r3n_mcp_…`) immediately — it is shown once. The UI keeps only a public prefix.

## stdio (local IDE)

Paste into Cursor / Claude Desktop / VS Code. Examples are in `r3ngine-mcp/config/`.

```json
{
  "mcpServers": {
    "r3ngine": {
      "command": "npx",
      "args": ["-y", "r3ngine-mcp"],
      "env": {
        "R3NGINE_URL": "https://<this-host>",
        "R3NGINE_MCP_API_KEY": "<shown-once-secret>"
      }
    }
  }
}
```

stdio talks to Django `/api/mcp/` directly. The sidecar is not required.

## HTTP

When transport is `http` or `both`, nginx `/mcp` proxies to the `r3ngine-mcp` container on port 3100 (internal only).

```
URL: https://<this-host>/mcp
Header: Authorization: Bearer <shown-once-secret>
```

If transport is `stdio` only, HTTP MCP returns 403 even though the nginx location exists.

Unauthorized HTTP clients (missing or invalid API key) are rate-limited **in the sidecar** before r3ngine is contacted: **10 failures per IP per minute** by default (`MCP_UNAUTH_MAX`, `MCP_UNAUTH_WINDOW_MS`). Further attempts get `429` with `Retry-After`. Invalid keys are remembered for the same window so Django is not probed again.

## Sessions and audit

The MCP process opens a session and heartbeats every 30 seconds. **Settings → MCP Access** lists connected agents. Click a row for the redacted request/response chain. **Revoke session** kicks that agent off without rotating the key. Heartbeats are not audited.

## What agents cannot do

Delete or edit targets, vulns, notes, users, or files. They cannot list keys, read audit events, or revoke sessions — those stay in this UI. MCP keys do not authenticate on `/api/action/` delete routes.

See also the [r3ngine-mcp README](../r3ngine-mcp/README.md).
