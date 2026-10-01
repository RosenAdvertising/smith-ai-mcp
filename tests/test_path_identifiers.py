"""Regression coverage for every ID-bearing client path call site.

The transport boundary is replaced, so rejected identifiers must fail before
any HTTP call, including a preliminary read in a merge/update operation.
"""

import inspect
from unittest.mock import Mock

import pytest
import requests
from smith_ai_mcp.client import SmithAIClient

CASES = [
    ("get_call", "call_id"),
    ("get_campaign", "campaign_id"),
    ("update_campaign", "campaign_id"),
    ("get_campaign_stats", "campaign_id"),
]


def client_and_arguments(method):
    client = object.__new__(SmithAIClient)
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"id": "normal-id", "success": true}'
    request = Mock(return_value={"id": "normal-id", "success": True})
    send = Mock(return_value=response)
    client._request = request
    client._send = send
    kwargs = {}
    for key, param in inspect.signature(getattr(client, method)).parameters.items():
        if param.default is not inspect.Parameter.empty or param.kind in (
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        ):
            continue
        annotation = str(param.annotation)
        if "dict" in annotation or key in {"body", "fields", "overlay"}:
            kwargs[key] = {"name": "probe"}
        elif "int" in annotation:
            kwargs[key] = 1
        else:
            kwargs[key] = "normal-id"
    if "resource" in kwargs:
        kwargs["resource"] = "matters"
    if "path" in kwargs:
        kwargs["path"] = "/tasks"
    if method == "tag_call":
        kwargs["tag_ids"] = [1]
    if method == "update_contact" and SmithAIClient.__name__ == "CloudTalkClient":
        kwargs["name"] = "probe"
    if method == "update_campaign":
        kwargs["name"] = "probe"
    return client, kwargs, request, send


@pytest.mark.parametrize(("method", "parameter"), CASES)
@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "a/../b", "%2e%2e", "a?b", "a#b", "a\\b", " ", "a\n", None, True],
)
def test_invalid_path_id_never_reaches_transport(method, parameter, value):
    client, kwargs, request, send = client_and_arguments(method)
    kwargs[parameter] = value
    with pytest.raises(Exception) as caught:
        getattr(client, method)(**kwargs)
    error = caught.value
    assert parameter in str(error) or getattr(error, "field", None) == parameter
    assert "identifier" in str(error) or "identifier" in getattr(error, "expected", "")
    request.assert_not_called()
    send.assert_not_called()


@pytest.mark.parametrize(("method", "parameter"), CASES)
@pytest.mark.parametrize(
    "value", ["normal-id", "550e8400-e29b-41d4-a716-446655440000", "123", 123]
)
def test_normal_path_id_reaches_transport(method, parameter, value):
    client, kwargs, request, send = client_and_arguments(method)
    kwargs[parameter] = value
    getattr(client, method)(**kwargs)
    calls = request.call_args_list + send.call_args_list
    assert calls
    assert any(str(value) in str(call) for call in calls)
