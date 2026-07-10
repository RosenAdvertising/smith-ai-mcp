# smith-ai-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-F59E0B.svg)](https://opensource.org/licenses/MIT)
[![9 tools](https://img.shields.io/badge/tools-9-22C55E.svg)](https://github.com/RosenAdvertising/smith-ai-mcp)
[![MCP](https://img.shields.io/badge/MCP-compatible-7C3AED.svg)](https://modelcontextprotocol.io)
[![Smith.ai](https://img.shields.io/badge/Smith.ai-Hybrid%20Receptionist-1D4ED8.svg)](https://smith.ai)

<!-- prettier-ignore -->
> [!IMPORTANT]
> **Built to spec — not yet verified against a live Smith.ai account.**
> This server was built from Smith.ai's public API documentation and passes its full offline test suite, but we don't currently have Smith.ai API access to verify behavior against the live API. Endpoint paths, parameters, and response shapes follow the documented spec. If you hit a discrepancy, please open an issue.
> Smith.ai's public API documentation is minimal; endpoint paths are based on docs.smith.ai and are low-confidence. Treat this server as experimental until verified against a live account.

MCP server for [Smith.ai](https://smith.ai) — outbound call requests, campaign management, and call record retrieval.

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
[Credential storage](#credential-storage)), and verifies the connection.

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
