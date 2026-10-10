# Smith.ai MCP server

[![CI](https://github.com/RosenAdvertising/smith-ai-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/RosenAdvertising/smith-ai-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-F59E0B.svg)](LICENSE)
[![MCP 2026-07-28](https://img.shields.io/badge/MCP-2026--07--28-7C3AED.svg)](https://modelcontextprotocol.io)
[![9 tools](https://img.shields.io/badge/tools-9-22C55E.svg)](https://github.com/RosenAdvertising/smith-ai-mcp)

Connect Claude and other MCP clients to Smith.ai to request outbound calls, manage outreach campaigns and retrieve call records.

Smith.ai MCP server is a [Model Context Protocol](https://modelcontextprotocol.io) server for [Smith.ai](https://smith.ai), the human and AI hybrid receptionist service. It registers 9 tools that read and write Smith.ai data. It runs over stdio by default, for desktop clients such as Claude Desktop, and offers an opt-in stateless Streamable HTTP mode that implements MCP specification 2026-07-28. Smith.ai credentials stay on the machine that runs the server: they come from the setup command and your operating system's keyring, never from the client. Smith.ai's API does not configure call routing, IVR trees or phone numbers; the server covers call records, outbound call requests and campaigns.

## Features

- **Call records**: list calls with date filters and retrieve a single call.
- **Outbound calls**: ask Smith.ai's receptionist team to place a call on your behalf.
- **Campaigns**: create, list, look up and update outreach campaigns.
- **Campaign stats**: pull performance statistics for a campaign.
- **Account**: read account information and settings.

## Tools

The server registers 9 tools.

| Tool | What it does |
| --- | --- |
| `get_account` | Account information and settings. |
| `list_calls` | Paginated call records (`limit` up to 100), with optional `date_from` and `date_to` filters in YYYY-MM-DD format. |
| `get_call` | One call record by ID. |
| `request_outbound_call` | Ask Smith.ai's receptionist team to place an outbound call. |
| `list_campaigns` | List outreach campaigns. |
| `get_campaign` | One campaign by ID. |
| `create_campaign` | Create an outreach campaign from a name, script and contact list. |
| `update_campaign` | Update a campaign's name, script or status. |
| `get_campaign_stats` | Performance statistics for a campaign. |

### Prompts and resources

The server also registers three prompts and three resources.

| Prompt | What it does |
| --- | --- |
| `receptionist_call_brief` | Briefs the receptionist team for a call, from a contact name and purpose. |
| `campaign_launch_checklist` | Checklist for launching a campaign, from a campaign name. |
| `call_outcome_summary` | Summarizes call outcomes between two dates. |

| Resource | What it provides |
| --- | --- |
| `smith-ai://campaigns` | Campaigns as JSON reference data. |
| `smith-ai://recent_calls` | The last 25 call records as JSON. |
| `smith-ai://security-notes` | Security notes for the server. |

## Requirements

- Python 3.10 or later.
- A Smith.ai account with an API key (in Smith.ai: **Dashboard → Settings → API**).
- An MCP client such as Claude Desktop.

## Installation

Install [uv](https://docs.astral.sh/uv/), then clone the repository and install its locked dependencies:

```bash
git clone https://github.com/RosenAdvertising/smith-ai-mcp.git
cd smith-ai-mcp
uv sync --locked
```

## Configuration

Run the setup command once. It prompts for your API key, saves it (see [Credential storage](#credential-storage)) and verifies the connection. Get your API key in Smith.ai under **Dashboard → Settings → API**.

```bash
uv run smith-ai-mcp-setup
```

Restart the MCP server after setup so it loads the new API key. Check the connection at any time:

```bash
uv run smith-ai-mcp-verify
```

Server messages that say to run `smith-ai-mcp-setup` mean `uv run smith-ai-mcp-setup` from your clone.

The server sends the key as a bearer token in the `Authorization` header. It reads these variables:

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `SMITH_API_KEY` | Yes (saved by setup) | Keyring, then `~/.smith-ai-mcp/.env` | Smith.ai API key. |
| `SMITH_AI_MCP_USE_KEYRING` | No | `1` | Set to `0`, `false`, `no` or `off` to skip the operating system keyring and use the `.env` file. |

### Credential storage

By default your API key (`SMITH_API_KEY`) is stored in your operating system's native secret store via the cross-platform [`keyring`](https://github.com/jaraco/keyring) library:

| OS | Backend |
| --- | --- |
| macOS | Keychain |
| Windows | Credential Manager |
| Linux | Secret Service (GNOME Keyring / KWallet) |

The secret is saved under the service name `smith-ai-mcp`. Nothing is written to disk in clear text.

**File fallback.** On a host with no keyring backend (for example a headless Linux box without Secret Service), or if you set `SMITH_AI_MCP_USE_KEYRING=0`, the key falls back to a `~/.smith-ai-mcp/.env` file with `0600` permissions:

```text
SMITH_API_KEY=your_api_key
```

On Windows, the file is stored in the user's profile and protected by Windows' default per-user access rules. On POSIX, files are created with `0600` permissions and writes fail closed if private permissions cannot be established.

**Read order.** A value set in the process environment is used as is. When `SMITH_API_KEY` is not set, the server reads the OS keyring, then the `~/.smith-ai-mcp/.env` file, once at startup. A key exported in your shell therefore overrides the keyring and the file, and the keyring entry written by setup is used only while the variable is unset.

**Pluggable backend.** `keyring` lets you point at any secret store. For example, install [`keyrings.cryptfile`](https://pypi.org/project/keyrings.cryptfile/) for an encrypted file backend, or a cloud backend, then select it with the standard `PYTHON_KEYRING_BACKEND` environment variable or a `keyringrc.cfg`. See the [keyring configuration docs](https://github.com/jaraco/keyring#configuring).

## Usage with Claude Desktop

Add the server to Claude Desktop's configuration file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "smith-ai": {
      "command": "uv",
      "args": ["run", "--locked", "--directory", "/absolute/path/to/smith-ai-mcp", "smith-ai-mcp"]
    }
  }
}
```

Replace `/absolute/path/to/smith-ai-mcp` with the path of your clone, then restart Claude Desktop. Any other stdio MCP client uses the same command and arguments.

## HTTP mode

Stdio is the default. Set `SMITH_AI_MCP_TRANSPORT=streamable-http` to serve the stateless Streamable HTTP transport from MCP specification 2026-07-28 at `/mcp`. Each request stands alone: no initialization handshake and no `Mcp-Session-Id`. Clients on earlier protocol versions are served on the same endpoint.

> **Security: this endpoint has no authentication and no TLS.** Anyone who can reach the port can run every tool, including write tools, with this server's vendor credentials. Keep the default loopback bind (`127.0.0.1`), or put the server behind an authenticating TLS proxy on a private network. `SMITH_AI_MCP_ALLOWED_HOSTS` and `SMITH_AI_MCP_ALLOWED_ORIGINS` protect against browser DNS rebinding, not against direct callers. A proxy in front of it needs connection and idle timeouts: a legacy-style `GET /mcp` with `Accept: text/event-stream` holds a stream open until the client disconnects.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SMITH_AI_MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http`. An empty value selects `stdio`. |
| `SMITH_AI_MCP_HOST` | `127.0.0.1` | Bind address. An empty value selects `127.0.0.1`. `127.0.0.1`, `localhost` and `::1` use the SDK's built-in Host and Origin checks; any other value requires `SMITH_AI_MCP_ALLOWED_HOSTS`. |
| `PORT` | `8080` | Port; must be an integer. |
| `SMITH_AI_MCP_ALLOWED_HOSTS` | unset | Comma-separated `Host` header values accepted on a non-loopback bind, such as `mcp.example.com:8080` or `mcp.example.com:*`. |
| `SMITH_AI_MCP_ALLOWED_ORIGINS` | unset | Comma-separated `Origin` values accepted on a non-loopback bind, such as `https://client.example.com`. Requests without an `Origin` header are accepted. |

Smith.ai credentials come from the same configuration as stdio (see [Configuration](#configuration)), never from the request.

```bash
SMITH_AI_MCP_TRANSPORT=streamable-http PORT=8080 uv run --locked smith-ai-mcp
```

Point the MCP client at `http://127.0.0.1:8080/mcp`.

To check the endpoint from a shell, list the tools:

```bash
curl -sS http://127.0.0.1:8080/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'MCP-Method: tools/list' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{},"io.modelcontextprotocol/clientInfo":{"name":"curl","version":"0"}}}}'
```

## Error handling

A failed tool call returns an MCP error result (`isError`) whose text starts with "Error executing tool" and the tool name, followed by a fixed message. The server never passes a Smith.ai response body, a request URL, a credential or a rejected input value back to the client. For example: "Error executing tool get_call: The requested Smith.ai resource was not found (HTTP 404). Check the resource ID."

| Situation | Message after the prefix |
| --- | --- |
| Credentials missing | "Missing SMITH_API_KEY. Run: smith-ai-mcp-setup. Restart the MCP server after setup." |
| Authentication rejected (HTTP 401) | "Smith.ai authentication failed (HTTP 401). Re-run smith-ai-mcp-setup to reconnect." |
| Access denied (HTTP 403) | "Smith.ai access denied: the connected account lacks permission for this action (or the authorization expired; re-run smith-ai-mcp-setup if so)." |
| Not found (HTTP 404) | "The requested Smith.ai resource was not found (HTTP 404). Check the resource ID." |
| Rate limited (HTTP 429) | After the retries below: "Smith.ai rate limit reached (HTTP 429). Retry after N seconds." |
| Any other HTTP error | "Smith.ai returned HTTP 500: service unavailable." The status varies, and the reason is a fixed phrase such as "request rejected", "conflict", "validation failed" or "service unavailable". |
| Redirect | "Smith.ai returned HTTP 302: redirect rejected." Redirects are never followed. |
| Response that is not JSON | "Smith.ai returned HTTP 200: invalid JSON response." |
| Cannot reach Smith.ai (read) | "Smith.ai could not be reached. Check connectivity and retry." |
| Cannot reach Smith.ai (write) | "Smith.ai could not be reached while submitting this change; the outcome is unknown. Check whether it completed before retrying." |
| Invalid arguments | A message such as "Argument validation error for 'limit': expected integer greater than or equal to 1 and less than or equal to 100." or "Invalid argument 'status': expected a non-empty string of at most 128 characters without controls." |
| Anything else | The prefix alone, with no detail. |

Every Smith.ai request has a 30-second timeout. On HTTP 429 the server waits for the `Retry-After` interval (10 seconds when the header is missing or unreadable) and retries, up to 3 times per request and 60 seconds of total waiting; if the next wait would exceed what is left, the tool returns the rate-limit message at once. The server does not retry timeouts, connection failures or 5xx responses. A call to a name that is not a registered tool returns "Unknown tool. Choose a name from tools/list." A failed resource read returns "Smith.ai resource was not found." or "Error reading Smith.ai resource."

At startup the server exits with a message on stderr and a non-zero status when `SMITH_AI_MCP_TRANSPORT` is neither `stdio` nor `streamable-http`, when `PORT` is not an integer, or when a non-loopback `SMITH_AI_MCP_HOST` is set without `SMITH_AI_MCP_ALLOWED_HOSTS`.

## What Smith.ai covers

Smith.ai is a human and AI hybrid receptionist service: real receptionists, assisted by AI, handle your calls. It is not a configurable voice AI agent, and the API does not let you program call routing, change IVR trees or provision phone numbers.

The server covers:

- Call records and call details.
- Outbound call requests, which Smith.ai's receptionist team places on your behalf.
- Outreach campaigns and their performance stats.

These are out of scope; use the Smith.ai dashboard for them:

- Inbound call routing configuration.
- Real-time agent behavior, or editing a script mid-call.
- Phone number provisioning or porting.
- Live call monitoring or transcription webhooks.

## Outbound call text

`instructions` (`request_outbound_call`) and `script` (`create_campaign`, `update_campaign`) are delivered as written to Smith.ai's receptionist team, who act on them during live calls. Use only text you trust, never text copied from web pages, documents or intake forms. The server rejects text longer than 2,000 characters and text that contains instruction-override phrases such as "ignore prior instructions".

## API notes

- Smith.ai's published API documentation is brief. Endpoint paths follow docs.smith.ai.
- The `/account` endpoint may not exist on every plan; `smith-ai-mcp-verify` falls back to `list_calls` when `/account` returns HTTP 400, 404 or 405.
- `update_campaign` requires at least one non-empty `name`, `script` or `status`. A supplied `status` may be any non-empty string of at most 128 characters with no control characters. Whitespace-only statuses are rejected; statuses are not restricted to a fixed set of values.

## Testing

The test suite runs offline and needs no Smith.ai account: every Smith.ai API call is answered by a test double for the `requests` session. It covers request limits and paging, input and path-identifier validation, error classification and rate-limit retries, credential file handling, the setup and verify commands, the stdio server, and the Streamable HTTP transport including the 2026-07-28 wire format, Host and Origin checks and stateless requests.

```bash
uv sync --locked
uv run --locked pytest -q
```

CI runs the suite on every push and pull request to `main`.

The tools follow Smith.ai's published API documentation and have not yet been run against a live Smith.ai account.

## License

MIT. See [LICENSE](LICENSE).
