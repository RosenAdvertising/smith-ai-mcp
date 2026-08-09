# MCP specification delta: 2025-11-25 to 2026-07-28

Research date: 2026-08-09. Sources are limited to the official MCP
specification and the official MCP Python SDK repository/documentation.

## Current target and migration release

This repository currently targets MCP `2025-11-25`:

- `pyproject.toml` declares `mcp>=1.28.1,<2`, and `uv.lock` resolves MCP Python
  SDK 1.28.1. Its installed `LATEST_PROTOCOL_VERSION` is `2025-11-25`.
- `smith_ai_mcp/server.py` constructs the v1 `FastMCP` server and calls its
  default stdio `run()` transport. It does not override protocol negotiation.
- The repository has no tracked protocol-version guard or protocol tests.

The official changelog says `2026-07-28` follows `2025-11-25`
([spec changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).
The implementation release is MCP Python SDK `2.0.0`, which supports
`2026-07-28` and earlier revisions from one server
([SDK release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0),
[migration guide](https://py.sdk.modelcontextprotocol.io/migration/)).

Verdicts below mean:

- **AFFECTS-US**: this server exposes or relies on the changed surface. The SDK
  may implement the wire behavior, but the migration must pin or test it.
- **NOT-APPLICABLE**: the feature or role is absent. This migration will not
  add it solely because the new revision permits it.

## Protocol negotiation and lifecycle

| Change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Modern protocol sessions and `Mcp-Session-Id` are removed. | **AFFECTS-US** | The stdio server must accept independent modern requests. Application state is already explicit in tool arguments and fresh API clients, not MCP sessions. |
| Modern `initialize` / `initialized` are removed; each request carries protocol version and client capabilities in `_meta`. | **AFFECTS-US** | SDK v2 must provide its dual-era dispatcher, and tests must exercise the self-describing modern path while retaining legacy negotiation. |
| Servers implement `server/discover`. | **AFFECTS-US** | This required discovery RPC must advertise the latest version, actual primitives, and no unused extensions. |
| Results carry `resultType` (`complete` or `input_required`). | **AFFECTS-US** | This server returns tool, resource, prompt, discovery, and list results; ordinary responses must serialize `resultType: complete`. |
| Server-initiated requests are replaced by Multi Round-Trip Requests. | **NOT-APPLICABLE** | No tool, resource, or prompt uses sampling, roots, elicitation, or another server-to-client request. |
| Modern `ping`, `logging/setLevel`, and `notifications/roots/list_changed` are removed. | **NOT-APPLICABLE** | None is implemented; Python application logs are not MCP logging notifications. |

## Transports and notifications

| Change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Streamable HTTP POST requires `Mcp-Method` and, for named operations, `Mcp-Name`; `x-mcp-header` is available. | **AFFECTS-US** | The current executable is stdio-only, but SDK v2's raw HTTP application is the conformance surface for testing the protocol kernel and required headers. No tool parameter needs `x-mcp-header`. |
| Standalone HTTP GET and resource subscribe/unsubscribe become `subscriptions/listen`. | **AFFECTS-US** | The high-level SDK advertises resource subscription and list-change capabilities. Preserve its dual-era mapping without adding an application publisher, bus, or event store. |
| SSE resumability and redelivery are removed. | **NOT-APPLICABLE** | No event store or resumability behavior exists. |
| Legacy HTTP+SSE is deprecated. | **NOT-APPLICABLE** | The application exposes stdio only; raw Streamable HTTP is used only in tests. |

## Capabilities and extensions

| Change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Client and server capabilities gain `extensions`. | **AFFECTS-US** | Discovery exposes this shape; no unused extension may be advertised. |
| Experimental tasks move to the tasks extension. | **NOT-APPLICABLE** | No task handlers or task-augmented tools exist. |
| Roots, Sampling, and Logging are deprecated. | **NOT-APPLICABLE** | None is declared or used. |
| Sampling `includeContext` values are deprecated. | **NOT-APPLICABLE** | Sampling is not used. |

## Tools, resources, prompts, and cache semantics

| Change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Tool, prompt, resource, resource-template list results and resource reads carry `ttlMs` and `cacheScope`. | **AFFECTS-US** | The server exposes tools, prompts, and resources. Preserve conservative SDK defaults (`ttlMs: 0`, `cacheScope: private`) rather than expanding retention. |
| `tools/list` should be deterministic. | **AFFECTS-US** | Nine registered tools must appear in stable order across repeated discovery. |
| Tool schemas use JSON Schema 2020-12 and `structuredContent` may be any JSON value. | **AFFECTS-US** | Decorators generate schemas and API mappings return structured dictionaries. SDK v2 owns the revised models; generated schemas and structured results require regression coverage. |
| Resource-not-found changes from `-32002` to Invalid Params `-32602`. | **AFFECTS-US** | The server exposes static resources; an unknown URI must use the new code. |
| URL elicitation completion and correlation change. | **NOT-APPLICABLE** | Elicitation is not used. |
| Generated schema numeric keywords are corrected. | **NOT-APPLICABLE** | The repository neither vendors nor directly validates against the generated MCP meta-schema. |

## Authorization and security

| Change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Authorization servers should return RFC 9207 `iss`; clients validate it. | **NOT-APPLICABLE** | This stdio server is neither an MCP authorization server nor an MCP OAuth client. Smith.ai API-key loading is downstream application authentication. |
| Dynamic Client Registration clients send `application_type`. | **NOT-APPLICABLE** | The repository performs no MCP client registration. |
| Persisted MCP client credentials are issuer-bound. | **NOT-APPLICABLE** | It stores no MCP client registration credentials. |
| DCR is deprecated in favor of Client ID Metadata Documents. | **NOT-APPLICABLE** | It neither hosts DCR nor acts as a dynamically registered MCP client. |

## Errors, metadata, and observability

| Change | Verdict | Repository-specific reason |
| --- | --- | --- |
| Reserved errors include HeaderMismatch `-32020`, MissingRequiredClientCapability `-32021`, and UnsupportedProtocolVersion `-32022`; unknown methods use `-32601`. | **AFFECTS-US** | SDK v2 must return the new codes. Tests cover reachable cases without inventing a capability-dependent feature solely to trigger `-32021`. |
| `_meta` formally carries W3C trace context. | **NOT-APPLICABLE** | No MCP `_meta` tracing integration exists; this migration will not add an observability feature. |

Governance and SEP workflow changes impose no runtime requirement. The formal
feature lifecycle is respected by not adopting deprecated Roots, Sampling,
Logging, HTTP+SSE, or DCR.
