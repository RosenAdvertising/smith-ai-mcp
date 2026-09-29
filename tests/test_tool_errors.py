from __future__ import annotations

import asyncio
import logging

import pytest
import requests
from mcp import Client
from mcp.types import TextContent

from smith_ai_mcp import client as client_module
from smith_ai_mcp import server
from smith_ai_mcp.client import (
    AuthenticationError,
    MissingCredentialsError,
    NotFoundError,
    RateLimitError,
    VendorHTTPError,
)


def _call(monkeypatch: pytest.MonkeyPatch, error: Exception):
    class FakeClient:
        def get_account(self):
            raise error

    monkeypatch.setattr(server, "_client", FakeClient)

    async def run():
        async with Client(server.mcp, cache=None) as client:
            return await client.call_tool("get_account", {})

    return asyncio.run(run())


@pytest.mark.parametrize(
    ("error", "text"),
    [
        (MissingCredentialsError(), "Missing SMITH_API_KEY. Run: smith-ai-mcp-setup"),
        (
            AuthenticationError(),
            "Smith.ai rejected the API key. Re-authorize with: smith-ai-mcp-setup",
        ),
        (
            VendorHTTPError(502, "service unavailable"),
            "Smith.ai returned HTTP 502: service unavailable.",
        ),
        (RateLimitError(17), "Smith.ai rate limit reached. Retry after 17 seconds."),
        (
            NotFoundError(),
            "The requested Smith.ai resource was not found. Check the resource ID.",
        ),
    ],
)
def test_classified_errors_are_actual_sdk_results(monkeypatch, error, text):
    result = _call(monkeypatch, error)
    assert result.is_error is True
    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == f"Error executing tool get_account: {text}"


def test_unknown_error_masked_and_logged_without_exception_data(monkeypatch, caplog):
    marker = "Bearer fake-secret private@example.invalid https://user:pass@host"
    with caplog.at_level(logging.WARNING):
        result = _call(monkeypatch, RuntimeError(marker))
    assert result.is_error is True
    assert isinstance(result.content[0], TextContent)
    assert (
        result.content[0].text
        == "Error executing tool get_account: Smith.ai tool failed unexpectedly. Check server logs and retry."
    )
    assert marker not in caplog.text
    assert any(
        record.__dict__.get("reason") == "unexpected_error" for record in caplog.records
    )


def test_argument_schema_error_is_sdk_result_and_names_argument():
    async def run():
        async with Client(server.mcp, cache=None) as client:
            return await client.call_tool("list_calls", {"page": 0})

    result = asyncio.run(run())
    assert result.is_error is True
    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == (
        "Error executing tool list_calls: 1 validation error for list_calls\n"
        "page\n  Input should be greater than or equal to 1 "
        "[type=greater_than_equal, input_value=None, input_type=NoneType]\n"
        "    For further information visit "
        "https://errors.pydantic.dev/2.13/v/greater_than_equal"
    )
    assert "input_value=0" not in result.content[0].text


def test_client_masks_vendor_body_and_rejects_unsafe_retry_after(monkeypatch):
    marker = "token=FAKE private@example.invalid https://secret.invalid/key"
    response = requests.Response()
    response.status_code = 503
    response._content = marker.encode()
    response.headers["Retry-After"] = marker
    client = object.__new__(client_module.SmithAIClient)

    class Session(requests.Session):
        def request(self, *_args, **_kwargs):
            return response

    client.session = Session()
    with pytest.raises(VendorHTTPError) as caught:
        client.get("/account")
    assert caught.value.status == 503
    assert marker not in str(caught.value)
    assert client_module._retry_after_seconds(response) == 10
