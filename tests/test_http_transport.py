"""In-process Streamable HTTP checks for MCP 2026-07-28."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
import requests
from mcp import Client

from smith_ai_mcp import client as client_module
from smith_ai_mcp import server

PROTOCOL_VERSION = "2026-07-28"
PROTOCOL_VERSION_META_KEY = "io.modelcontextprotocol/protocolVersion"
CLIENT_CAPABILITIES_META_KEY = "io.modelcontextprotocol/clientCapabilities"
CLIENT_INFO_META_KEY = "io.modelcontextprotocol/clientInfo"
SERVER_INFO_META_KEY = "io.modelcontextprotocol/serverInfo"
LOOPBACK_BASE_URL = "http://127.0.0.1:8080"


@pytest.fixture(autouse=True)
def _isolated_transport_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "SMITH_AI_MCP_TRANSPORT",
        "SMITH_AI_MCP_HOST",
        "SMITH_AI_MCP_ALLOWED_HOSTS",
        "SMITH_AI_MCP_ALLOWED_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)


def _modern_request(
    method: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: int = 1,
) -> tuple[dict[str, str], dict[str, Any]]:
    request_params = dict(params or {})
    request_params["_meta"] = {
        PROTOCOL_VERSION_META_KEY: PROTOCOL_VERSION,
        CLIENT_CAPABILITIES_META_KEY: {},
        CLIENT_INFO_META_KEY: {"name": "smith-ai-http-test", "version": "0"},
    }
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": PROTOCOL_VERSION,
        "mcp-method": method,
    }
    if method in {"tools/call", "prompts/get"}:
        headers["mcp-name"] = str(request_params["name"])
    elif method == "resources/read":
        headers["mcp-name"] = str(request_params["uri"])
    return headers, {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": request_params,
    }


def _payload(response: httpx.Response) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        data_lines = [
            line[len("data:") :].strip()
            for line in response.text.splitlines()
            if line.startswith("data:")
        ]
        assert data_lines, response.text
        return json.loads(data_lines[-1])
    return response.json()


def _result(response: httpx.Response) -> dict[str, Any]:
    assert response.status_code == 200, response.text
    payload = _payload(response)
    assert payload["jsonrpc"] == "2.0"
    return payload["result"]


async def _post_with(
    client: httpx.AsyncClient,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: int = 1,
) -> httpx.Response:
    headers, body = _modern_request(method, params, request_id=request_id)
    return await client.post("/mcp", headers=headers, json=body)


@asynccontextmanager
async def _client(app: Any, base_url: str = LOOPBACK_BASE_URL):
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as client:
            yield client


async def _post(
    app: Any,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    base_url: str = LOOPBACK_BASE_URL,
) -> httpx.Response:
    async with _client(app, base_url) as client:
        return await _post_with(client, method, params)


def test_http_tools_list_matches_stdio() -> None:
    async def run() -> tuple[list[tuple[str, dict[str, Any]]], httpx.Response]:
        async with Client(server.mcp, cache=None) as client:
            listed = await client.list_tools()
        stdio = [
            (
                tool.name,
                tool.model_dump(by_alias=True, mode="json", exclude_none=True)[
                    "inputSchema"
                ],
            )
            for tool in listed.tools
        ]
        response = await _post(server.create_serve_app(), "tools/list")
        return stdio, response

    stdio, response = asyncio.run(run())
    http_tools = [
        (tool["name"], tool["inputSchema"]) for tool in _result(response)["tools"]
    ]
    assert http_tools == stdio


def test_read_tool_runs_over_http_against_vendor_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMITH_API_KEY", "fake-test-key")
    vendor = requests.Response()
    vendor.status_code = 200
    vendor._content = b'{"account":"firm"}'
    vendor.headers["Content-Type"] = "application/json"

    class Session(requests.Session):
        def request(self, *_args: Any, **_kwargs: Any) -> requests.Response:
            return vendor

    monkeypatch.setattr(client_module.requests, "Session", Session)
    response = asyncio.run(
        _post(
            server.create_serve_app(),
            "tools/call",
            {"name": "get_account", "arguments": {}},
        )
    )
    result = _result(response)
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == {"account": "firm"}


def test_two_requests_share_no_session() -> None:
    async def run() -> tuple[httpx.Response, httpx.Response, int]:
        app = server.create_serve_app()
        async with _client(app) as client:
            first = await _post_with(client, "tools/list", request_id=1)
            second = await _post_with(client, "tools/list", request_id=2)
            sessions = len(server.mcp.session_manager._server_instances)
            return first, second, sessions

    first, second, sessions = asyncio.run(run())
    assert sessions == 0
    assert server.mcp.session_manager.stateless is True
    for response in (first, second):
        assert response.status_code == 200
        names = {name.lower() for name in response.headers}
        assert "mcp-session-id" not in names
    assert _result(first)["tools"] == _result(second)["tools"]


def test_bogus_transport_exits_and_default_is_stdio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMITH_AI_MCP_TRANSPORT", "bogus")
    with pytest.raises(SystemExit) as caught:
        server.main()
    message = str(caught.value)
    assert "stdio" in message
    assert "streamable-http" in message

    monkeypatch.delenv("SMITH_AI_MCP_TRANSPORT", raising=False)
    called: list[str] = []
    monkeypatch.setattr(server.mcp, "run", lambda: called.append("stdio"))
    server.main()
    assert called == ["stdio"]


def test_allowed_host_rejects_other_host_and_bad_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMITH_AI_MCP_HOST", "10.1.2.3")
    monkeypatch.setenv("SMITH_AI_MCP_ALLOWED_HOSTS", "app.internal:8080")

    async def run() -> tuple[httpx.Response, httpx.Response]:
        other = await _post(
            server.create_serve_app(), "tools/list", base_url="http://other.example"
        )
        async with _client(
            server.create_serve_app(), "http://app.internal:8080"
        ) as client:
            headers, body = _modern_request("tools/list")
            headers["origin"] = "https://evil.example"
            denied = await client.post("/mcp", headers=headers, json=body)
        return other, denied

    other, denied = asyncio.run(run())
    assert other.status_code == 421
    assert denied.status_code == 403


def test_non_loopback_host_without_allowed_hosts_exits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMITH_AI_MCP_HOST", "0.0.0.0")
    with pytest.raises(SystemExit) as caught:
        server.create_serve_app()
    assert "SMITH_AI_MCP_ALLOWED_HOSTS" in str(caught.value)


def test_non_integer_port_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "nope")
    with pytest.raises(SystemExit) as caught:
        server._port()
    assert "PORT" in str(caught.value)
    assert "nope" in str(caught.value)


def test_get_and_delete_are_rejected_and_discover_names_version() -> None:
    async def run() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        app = server.create_serve_app()
        async with _client(app) as client:
            headers = {
                "accept": "application/json, text/event-stream",
                "mcp-protocol-version": PROTOCOL_VERSION,
            }
            get_response = await client.get("/mcp", headers=headers)
            delete_response = await client.delete("/mcp", headers=headers)
            discover = await _post_with(client, "server/discover")
            return get_response, delete_response, discover

    get_response, delete_response, discover = asyncio.run(run())
    assert get_response.status_code == 405
    assert delete_response.status_code == 405
    result = _result(discover)
    assert PROTOCOL_VERSION in result["supportedVersions"]
    version = result["_meta"][SERVER_INFO_META_KEY]["version"]
    assert isinstance(version, str) and version


def test_stateless_lifespan_runs_once_for_two_requests() -> None:
    calls = {"n": 0}
    original = server.mcp._lowlevel_server.lifespan

    @asynccontextmanager
    async def counting(app: Any):
        calls["n"] += 1
        async with original(app) as state:
            yield state

    server.mcp._lowlevel_server.lifespan = counting
    try:

        async def run() -> None:
            app = server.create_serve_app()
            async with _client(app) as client:
                await _post_with(client, "tools/list", request_id=1)
                await _post_with(client, "tools/list", request_id=2)

        asyncio.run(run())
    finally:
        server.mcp._lowlevel_server.lifespan = original
    assert calls["n"] == 1


def test_empty_transport_selects_stdio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for raw in ("", "   "):
        monkeypatch.setenv("SMITH_AI_MCP_TRANSPORT", raw)
        assert server._requested_transport() == "stdio"
    monkeypatch.setenv("SMITH_AI_MCP_TRANSPORT", "")
    called: list[str] = []
    monkeypatch.setattr(server.mcp, "run", lambda: called.append("stdio"))
    server.main()
    assert called == ["stdio"]


def test_empty_host_yields_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    for raw in ("", "   "):
        monkeypatch.setenv("SMITH_AI_MCP_HOST", raw)
        assert server._host() == "127.0.0.1"


def test_uppercase_localhost_is_non_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SMITH_AI_MCP_HOST", "LOCALHOST")
    assert server._host() == "LOCALHOST"
    with pytest.raises(SystemExit) as caught:
        server.create_serve_app()
    assert "SMITH_AI_MCP_ALLOWED_HOSTS" in str(caught.value)


def test_server_import_survives_missing_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib
    import importlib.metadata

    def _missing(*_args: object, **_kwargs: object) -> str:
        raise importlib.metadata.PackageNotFoundError()

    monkeypatch.setattr(importlib.metadata, "version", _missing)
    reloaded = importlib.reload(server)
    assert reloaded is server
