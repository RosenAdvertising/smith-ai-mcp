# smith-ai-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-F59E0B.svg)](https://opensource.org/licenses/MIT)
[![9 tools](https://img.shields.io/badge/tools-9-22C55E.svg)](https://github.com/RosenAdvertising/smith-ai-mcp)
[![MCP](https://img.shields.io/badge/MCP-compatible-7C3AED.svg)](https://modelcontextprotocol.io)
[![Smith.ai](https://img.shields.io/badge/Smith.ai-Hybrid%20Receptionist-1D4ED8.svg)](https://smith.ai)

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

This prompts for your API key, saves it to `~/.smith-ai-mcp/.env`, and verifies the connection.

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

Bearer token via `Authorization: Bearer {SMITH_API_KEY}`. Key is loaded from `~/.smith-ai-mcp/.env` at startup, with fallback to the `SMITH_API_KEY` environment variable.

---

## Notes

- Smith.ai's API documentation is minimal. Endpoint paths are based on docs.smith.ai — verify against your account before relying on them in production.
- The `/account` endpoint may not exist in all plans; the verify script falls back to `list_calls` if it fails.
- Rate limiting: automatic retry up to 3 times, respecting `Retry-After` headers.
