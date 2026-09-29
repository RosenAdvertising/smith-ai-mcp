# MCP 2026-07-28 migration

This server targets MCP protocol `2026-07-28` through Python SDK
`mcp>=2.2,<3`. `uv.lock` resolves `mcp` and its `mcp-types` companion to
`2.2.0`. The stdio entry point uses `MCPServer` and `mcp.run()`.

The migration retains nine tools, three resources, three prompts, API-key
resolution, fresh API clients, retries, and conservative cache behavior. List
tools accept page numbers from 1 and limits from 1 through 100; each call
forwards the limit in one upstream request. Receptionist-facing text fields,
including `update_campaign.script`, use the trusted-text length and pattern
checks. Rejection logs use reason codes without tool values or response bodies.

## Protocol coverage

The offline ASGI tests exercise sessionless `server/discover`, per-request
protocol and client metadata, required HTTP method/name headers, discovery and
list cache metadata (`ttlMs: 0`, `cacheScope: private`), deterministic tool
listing, tool results, error codes, and modern and legacy negotiation. The
SDK maps advertised resource subscription and list-change capabilities; this
application adds no publisher or event store. The executable uses stdio;
Streamable HTTP is exercised in-process for protocol checks.

Smith.ai endpoint paths, response shapes, and ordering remain unverified
against a live account. The list tools do not add a speculative sort option.
The [specification delta](SPEC-DELTA-2026-07-28.md) maps protocol changes to
this server.

## Reproduce the offline checks

With the locked development dependencies installed in `.venv` and Ruff on
`PATH`, run:

```bash
SMITH_AI_MCP_USE_KEYRING=0 SMITH_API_KEY=offline-test-placeholder .venv/bin/python -m pytest -q
SMITH_AI_MCP_USE_KEYRING=0 SMITH_API_KEY=offline-test-placeholder .venv/bin/python tests/spec_check.py --mcp-only
ruff check smith_ai_mcp/client.py smith_ai_mcp/credentials.py smith_ai_mcp/server.py smith_ai_mcp/setup/setup.py smith_ai_mcp/setup/verify.py tests/spec_check.py tests/test_canary_hardening.py tests/test_spec_2026_07_28.py
uv lock --check --offline
```

The tests use fake Smith.ai responses and an in-process protocol transport.
These commands make no live Smith.ai requests.

## Public error behavior

Tool failures return MCP error results with `isError=true`. The server exposes
fixed, classified messages for missing credentials, authentication rejection,
access denial, rate limits, not-found responses, known HTTP failures, transport
failures, and safe argument validation. Unknown failures use the generic text
`Error executing tool <name>`; exception text, request URLs, credentials, and
vendor response bodies are not included. Resource failures use a fixed public
message and do not expose the underlying exception.
