# smith-ai-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-F59E0B.svg)](https://opensource.org/licenses/MIT)
[![9 tools](https://img.shields.io/badge/tools-9-22C55E.svg)](https://github.com/RosenAdvertising/smith-ai-mcp)
[![MCP](https://img.shields.io/badge/MCP-compatible-7C3AED.svg)](https://modelcontextprotocol.io)
[![Smith.ai](https://img.shields.io/badge/Smith.ai-Hybrid%20Receptionist-1D4ED8.svg)](https://smith.ai)

<!-- prettier-ignore -->
> [!IMPORTANT]
> **Built to spec — not yet verified against a live Smith.ai account.**
> This server was built from Smith.ai's public API documentation and includes offline tests, but we don't currently have Smith.ai API access to verify behavior against the live API. Endpoint paths, parameters, and response shapes follow the documented spec. If you hit a discrepancy, please open an issue.
> Smith.ai's public API documentation is minimal; endpoint paths are based on docs.smith.ai and are low-confidence. Treat this server as experimental until verified against a live account.

MCP server for [Smith.ai](https://smith.ai) — outbound call requests, campaign management, and call record retrieval.

Requires Python MCP SDK `>=2.3,<3` for the MCP 2026-07-28 protocol support.

## What Smith.ai is (and isn't)

Smith.ai is a **human + AI hybrid receptionist service**. Real receptionists — assisted by AI — handle your calls. This is not a configurable voice AI agent. You cannot program call routing logic, change IVR trees, or provision phone numbers through the API.

What the API (and this MCP) covers:

- Retrieve call records and call details
- Request outbound calls — Smith's receptionist team places them on your behalf
- Create and manage outreach campaigns
- Pull campaign performance stats

What is out of scope:

- Inbound call routing configuration
- Real-time agent behavior or script editing mid-call
- Phone number provisioning or porting
- Live call monitoring or transcription webhooks

If you need those, use the Smith.ai dashboard directly.

---

## Installation

```bash
cd smith-ai-mcp
pip install -e .
```

### Configure

```bash
smith-ai-mcp-setup
```

This prompts for your API key, saves it to your OS keyring (see
[Credential storage](#credential-storage)), and verifies the connection. Restart
the MCP server after setup so it loads the new API key.

Get your API key at: **smith.ai → Dashboard → Settings → API**

### Verify

```bash
smith-ai-mcp-verify
```

---

## Claude Desktop config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "smith-ai": {
      "command": "smith-ai-mcp"
    }
  }
}
```

---

## HTTP mode

Stdio stays the default. Set `SMITH_AI_MCP_TRANSPORT=streamable-http` to serve
stateless Streamable HTTP (MCP 2026-07-28) at `POST /mcp`. Credentials are the
same environment variables as stdio. The server never reads them from the
request.

> **Security: this endpoint has no authentication and no TLS.** Anyone who can reach the port can run every tool, including write and delete tools, with this server's vendor credentials. Keep the default loopback bind (`127.0.0.1`), or put the server behind an authenticating TLS proxy on a private network. `SMITH_AI_MCP_ALLOWED_HOSTS` and `SMITH_AI_MCP_ALLOWED_ORIGINS` protect against browser DNS rebinding, not against direct callers. A proxy in front of it needs connection and idle timeouts: a legacy-style `GET /mcp` with `Accept: text/event-stream` holds a stream open until the client disconnects.

| Variable                       | Default     | Purpose                                                                    |
| ------------------------------ | ----------- | -------------------------------------------------------------------------- |
| `SMITH_AI_MCP_TRANSPORT`       | `stdio`     | `stdio` or `streamable-http`                                               |
| `SMITH_AI_MCP_HOST`            | `127.0.0.1` | Bind address. `127.0.0.1`, `localhost`, and `::1` are loopback             |
| `PORT`                         | `8080`      | Bind port. A non-integer value exits                                       |
| `SMITH_AI_MCP_ALLOWED_HOSTS`   |             | Comma-separated Host values. Required when the bind address is not loopback |
| `SMITH_AI_MCP_ALLOWED_ORIGINS` |             | Optional comma-separated Origin values checked with those hosts           |
| `SMITH_API_KEY`                |             | Smith.ai bearer token                                                      |
| `SMITH_AI_MCP_USE_KEYRING`     | `1`         | Set to `0` to skip the OS keyring and use the `~/.smith-ai-mcp/.env` file |

```bash
SMITH_AI_MCP_TRANSPORT=streamable-http PORT=8080 smith-ai-mcp
```

```bash
curl -sS http://127.0.0.1:8080/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'MCP-Method: tools/list' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/clientInfo":{"name":"curl","version":"0"}}}}'
```

---

## Tools (9 total)

| Tool                    | Description                                       |
| ----------------------- | ------------------------------------------------- |
| `get_account`           | Account info and settings                         |
| `list_calls`            | Paginated call records with optional date filters |
| `get_call`              | Single call record by ID                          |
| `request_outbound_call` | Ask Smith to place an outbound call               |
| `list_campaigns`        | List outreach campaigns                           |
| `get_campaign`          | Single campaign details                           |
| `create_campaign`       | Create a new outreach campaign                    |
| `update_campaign`       | Update name, script, or status                    |
| `get_campaign_stats`    | Campaign performance stats                        |

---

## Auth

Bearer token via `Authorization: Bearer {SMITH_API_KEY}`. At startup the key is
resolved in the order **OS keyring → `SMITH_API_KEY` environment variable →
`~/.smith-ai-mcp/.env` file**. See [Credential storage](#credential-storage) for
how it is stored and how to point at your own secret backend.

---

## Credential storage

By default your API key (`SMITH_API_KEY`) is stored in your operating system's
native secret store via the cross-platform
[`keyring`](https://github.com/jaraco/keyring) library:

| OS      | Backend                                  |
| ------- | ---------------------------------------- |
| macOS   | Keychain                                 |
| Windows | Credential Manager                       |
| Linux   | Secret Service (GNOME Keyring / KWallet) |

The secret is saved under the service name `smith-ai-mcp`. Nothing is written to
disk in clear text.

**File fallback.** On a host with no keyring backend (e.g. a headless Linux box
without Secret Service), or if you set `SMITH_AI_MCP_USE_KEYRING=0`, the key
falls back to a `~/.smith-ai-mcp/.env` file with `0600` permissions:

```text
SMITH_API_KEY=your_api_key
```

On Windows, the file is stored in the user's profile and protected by Windows'
default per-user access rules. On POSIX, files are created with `0600` permissions
and writes fail closed if private permissions cannot be established.

**Read order.** Values resolve in the order OS keyring → process environment →
`.env` file. So a rotated key in the keyring always wins, and a value exported in
your shell overrides the file fallback without touching the keyring.

**Pluggable backend.** `keyring` lets you point at any secret store. For example,
install [`keyrings.cryptfile`](https://pypi.org/project/keyrings.cryptfile/) for
an encrypted file backend, or a cloud backend, then select it with the standard
`PYTHON_KEYRING_BACKEND` environment variable or a `keyringrc.cfg`. See the
[keyring configuration docs](https://github.com/jaraco/keyring#configuring).

---

## Notes

- Smith.ai's API documentation is minimal. Endpoint paths are based on docs.smith.ai — verify against your account before relying on them in production.
- The `/account` endpoint may not exist in all plans; the verify script falls back to `list_calls` if it fails.
- Rate limiting: automatic retry up to 3 times, respecting `Retry-After` headers.

`update_campaign` requires at least one non-empty `name`, `script`, or `status`.
A supplied `status` may be any non-empty string of at most 128 characters,
with no control characters. Whitespace-only statuses are rejected; statuses
are not restricted to a fixed set of values.
