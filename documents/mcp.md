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
        "R3NGINE_MCP_API_KEY": "<shown-once-secret>",
        "R3NGINE_CA_CERT": "<full-path-to-ca.crt>",
        "NODE_EXTRA_CA_CERTS": "<full-path-to-ca.crt>"
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

## Install locally

From r3ngine (clones `r3ngine-mcp/` if needed, then runs the Node setup):

```bash
node scripts/install-mcp.mjs --url https://<this-host> --key r3n_mcp_… --yes --write-cursor
```

Windows: `.\scripts\install-mcp.ps1 --url https://<this-host> --key r3n_mcp_… --yes`

From a checkout of r3ngine-mcp:

```bash
npm run setup -- --url https://<this-host> --key r3n_mcp_… --yes
```

The setup script installs dependencies, builds `dist/`, writes `.env`, opens a throwaway MCP session against `/api/mcp/` to prove the key works, smoke-starts the process, and can merge Cursor / VS Code / Claude Desktop config.

On a local checkout the installer uses the **full path** to **`secrets/certs/ca.crt`** and writes it into `.env` and MCP client env (`R3NGINE_CA_CERT` / `NODE_EXTRA_CA_CERTS`) so agents know where the cert is. It verifies TLS as the DNS name in **`secrets/certs/r3ngine.pem`** (your `DOMAIN_NAME`). Connecting to `https://127.0.0.1` is supported; the cert itself is issued for that domain, not the loopback IP.

If this machine does not have that file, setup tells you to copy `secrets/certs/ca.crt` from the r3ngine host and asks for the **full local path** (or pass `--ca C:\full\path\to\ca.crt`). Suggested destination: `r3ngine-mcp/certs/ca.crt`. Setup will not continue over HTTPS until agents have that path.

Unauthorized HTTP clients (missing or invalid API key) are rate-limited **in the sidecar** before r3ngine is contacted: **10 failures per IP per minute** by default (`MCP_UNAUTH_MAX`, `MCP_UNAUTH_WINDOW_MS`). Further attempts get `429` with `Retry-After`. Invalid keys are remembered for the same window so Django is not probed again.

## Sessions and audit

The MCP process opens a session and heartbeats every 30 seconds. **Settings → MCP Access** lists connected agents grouped by a fingerprint of provider + device (OS, IDE, hostname). Click a row for the redacted request/response chain. Click the **key name** to jump to that API key. **Ban** blocks that fingerprint from reconnecting even with a new session. Sys-admins can **Delete** an agent (this removes audit logs) and choose to **keep the ban** or **unban**. Heartbeats are not audited.

## What agents cannot do

Delete or edit targets, vulns, notes, users, or files. They cannot list keys, read audit events, or revoke sessions — those stay in this UI. MCP keys do not authenticate on `/api/action/` delete routes.

See also the [r3ngine-mcp README](../r3ngine-mcp/README.md).
