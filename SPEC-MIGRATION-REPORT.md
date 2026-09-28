# MCP 2026-07-28 migration report

## Result

`smith-ai-mcp` now targets MCP `2026-07-28`, up from `2025-11-25`. The
direct Python SDK dependency changed from `mcp>=1.28.1,<2` (locked to 1.28.1)
to the exact migration release `mcp==2.0.0`; the lock now includes
`mcp-types==2.0.0`.

The repository was not already conformant, so this was a migration rather than
a no-op. The authoritative repository-specific classification is in
[`SPEC-DELTA-2026-07-28.md`](SPEC-DELTA-2026-07-28.md). The SDK changes follow
the [official v2 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0)
and [migration guide](https://py.sdk.modelcontextprotocol.io/migration/).

No deployment, live Smith.ai account, credential, GitHub write, push, or
out-of-scope backup directory was touched.

## Implementation

- Replaced v1 `FastMCP` with v2 `MCPServer`. The existing stdio entry point
  remains `mcp.run()`, which preserves the repository's transport posture.
- Kept all nine tools, three resources, three prompts, API-key resolution,
  fresh-client state model, retry policy, and conservative cache behavior.
- Added schema-enforced list controls: page numbers are at least 1 and limits
  are 1 through 100. Each list client still makes exactly one upstream request,
  so the limit is not reused as an auto-pagination page size.
- Applied the existing trusted-text validation to `update_campaign.script`,
  closing a guard gap for the same receptionist-facing field.
- Added PII-free reason logs to rejection paths. Logs contain stable reason
  codes, safe field names, and status codes, never tool values, response
  bodies, names, email addresses, phone numbers, or credentials.
- Removed account name/email output from verification, raw upstream response
  bodies from exceptions, and partial API-key display from setup.
- Added a locked development group for the offline pytest/HTTP harness.

## Protocol conformance

The raw ASGI-wire suite verifies:

- sessionless `server/discover` for `2026-07-28` and the absence of
  `Mcp-Session-Id`;
- modern per-request protocol/client metadata;
- required `MCP-Protocol-Version`, `Mcp-Method`, and named-operation
  `Mcp-Name` headers, including header mismatch `-32020`;
- discovery/list/read `resultType`, `ttlMs: 0`, and `cacheScope: private`;
- deterministic discovery of all nine tools and bounded list schemas;
- JSON tool content plus `resultType: complete`;
- resource-not-found Invalid Params `-32602`, unsupported version `-32022`,
  and unknown method `-32601`;
- modern default negotiation and legacy `2025-11-25` negotiation from the
  same server; and
- a lightweight guard that pins both the SDK latest version and modern-version
  tuple to `2026-07-28`.

SDK-managed resource subscription and list-change capabilities remain enabled,
allowing v2 to map them to the modern subscription transport while serving
legacy clients. No publisher, event bus, session store, extension, MRTR flow,
or new feature was added.

## Canary checks

### A. List-tool limit and order — FIXED, with ordering method-unverified

Both list tools now expose bounded page/limit schemas. Regression tests prove
invalid values are rejected, the exact limit is forwarded, and only one
upstream request is made. Neither the repository nor the permitted official
MCP research sources establish Smith.ai sort parameter names or whether the
vendor defaults oldest-first. No speculative order parameter was added; this
remains honestly flagged for verification against authoritative Smith.ai API
documentation or a live account.

### B. Silent rejections — FIXED

Trusted-text length/injection guards, invalid contact-list type, missing or
invalid API key, non-JSON response, upstream error, and keyring-delete fallback
paths now emit PII-free reason events before rejecting or degrading. Tests
assert reason visibility and the absence of private marker values.

### C. Origin/CSP ceremony — N/A

This repository serves no browser pages, forms, callbacks, or custom HTTP
middleware. Its application entry point is stdio; the Streamable HTTP app is
constructed only as an in-process protocol conformance harness.

### D. PII in logs/output — FIXED

No `sub` logging exists. Verification no longer prints account name/email,
client exceptions no longer include raw upstream bodies, and setup no longer
echoes even masked API-key fragments. Regression tests inject marker identity
data and prove it does not reach logs, exceptions, or verification output.

## Verification

Baseline on `main` at `34fb20e`:

- SDK 1.28.1, latest protocol `2025-11-25`, v1 `FastMCP`.
- `pytest`: **0/0 tests** (no tests collected; exit 5 because the repository
  had no tracked test suite).
- Repository-configured Ruff 0.8.5: passed.

Migrated branch:

- `uv sync --locked`: passed on Python 3.12.
- `uv run pytest -q`: **22/22 passed**.
- `uv run python tests/spec_check.py --mcp-only`: passed.
- current `uvx ruff check .`: passed.
- current `uvx ruff format --check .`: passed.

The tests are entirely offline. Smith.ai endpoint paths, response shapes, and
ordering support remain method-verified only; no live Smith.ai account was
available or required.

## Git sandbox fallback

The runtime denied writes to the repository's own `.git` directory while
creating `refs/heads/spec-2026-07-28.lock`. The complete branch history was
therefore built in the authorized scratchpad alternate Git database against
the same worktree. A verified portable bundle is exported to the task's
scratchpad as `smith-ai-spec-2026-07-28.bundle`; it must be imported into the
original repository to materialize the local branch there. Nothing was pushed.

## Commit structure

- `docs: document MCP 2026-07-28 delta`
- `feat: migrate server to MCP 2026-07-28`
- `test: prove MCP 2026-07-28 conformance`
- `docs: report MCP 2026-07-28 migration`

Every migration commit includes the requested
`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` trailer.
