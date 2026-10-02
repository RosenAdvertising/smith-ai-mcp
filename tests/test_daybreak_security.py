"""Daybreak review probes at the registered MCP or real setup/storage boundary."""

import asyncio
import os
import stat
from unittest.mock import Mock

import pytest
from mcp.types import CallToolRequestParams
from smith_ai_mcp import client, credentials, server


def invoke(name, arguments):
    return asyncio.run(
        server.mcp._handle_call_tool(
            None, CallToolRequestParams(name=name, arguments=arguments)
        )
    )


def text(result):
    return " ".join(part.text for part in result.content if hasattr(part, "text"))


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("failure", [None, "chmod", "fchmod", "replace"])
def test_setup_secret_file_is_private_and_atomic(
    monkeypatch, tmp_path, existing, failure
):
    target = tmp_path / ".env"
    if existing:
        target.write_text("PROBE=old\n")
        target.chmod(0o644)
    monkeypatch.setattr(credentials, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(credentials, "ENV_FILE", target)
    monkeypatch.setattr(credentials, "_keyring_enabled", lambda: False)

    def save():
        credentials.set_secret("PROBE", "synthetic-value")

    original_open = os.open
    original_replace = os.replace
    seen_modes = []

    def checked_open(path, flags, mode=0o777, *args, **kwargs):
        fd = original_open(path, flags, mode, *args, **kwargs)
        if str(path).endswith(".tmp"):
            seen_modes.append(stat.S_IMODE(os.fstat(fd).st_mode))
            assert mode == 0o600
            assert os.fstat(fd).st_size == 0
        return fd

    def fail(*args, **kwargs):
        raise PermissionError("simulated permission failure")

    def checked_replace(source, dest):
        assert stat.S_IMODE(source.stat().st_mode) == 0o600
        assert "synthetic-value" in source.read_text()
        assert target.read_text() == "PROBE=old\n" if existing else not target.exists()
        return original_replace(source, dest)

    monkeypatch.setattr(os, "open", checked_open)
    monkeypatch.setattr(os, "replace", checked_replace)
    if failure == "chmod":
        monkeypatch.setattr(os, "chmod", fail)
    elif failure == "fchmod":
        monkeypatch.setattr(os, "fchmod", fail)
    elif failure == "replace":
        monkeypatch.setattr(os, "replace", fail)
    previous = os.umask(0o022)
    try:
        if failure in {"fchmod", "replace"}:
            with pytest.raises(PermissionError):
                save()
            assert (
                target.read_text() == "PROBE=old\n" if existing else not target.exists()
            )
        else:
            save()
            assert stat.S_IMODE(target.stat().st_mode) == 0o600
            assert "synthetic-value" in target.read_text()
    finally:
        os.umask(previous)
    assert seen_modes == [0o600]
    assert not list(tmp_path.glob(".*.tmp"))


@pytest.mark.parametrize("fields", [{}, {"name": " ", "script": " ", "status": " "}])
def test_empty_update_never_constructs_client(monkeypatch, fields):
    factory = Mock(side_effect=AssertionError("no client for empty update"))
    monkeypatch.setattr(server, "_client", factory)
    result = invoke("update_campaign", {"campaign_id": "probe", **fields})
    assert result.is_error
    assert "at least one" in text(result)
    factory.assert_not_called()


@pytest.mark.parametrize(
    "field,value", [("name", "probe"), ("script", "probe"), ("status", "active")]
)
def test_explicit_update_reaches_transport(monkeypatch, field, value):
    api = object.__new__(client.SmithAIClient)
    api._request = Mock(return_value={"ok": True})
    api.patch = Mock(return_value={"ok": True})
    monkeypatch.setattr(server, "_client", lambda: api)
    result = invoke("update_campaign", {"campaign_id": "probe", field: value})
    assert not result.is_error, text(result)
    assert api._request.called or api.patch.called


@pytest.mark.parametrize("status", [" ", "x" * 129, "active\n", "a\x00b", "a\x7fb"])
def test_campaign_status_rejected_at_mcp(monkeypatch, status):
    factory = Mock()
    monkeypatch.setattr(server, "_client", factory)
    result = invoke(
        "update_campaign", {"campaign_id": "probe", "name": "probe", "status": status}
    )
    assert result.is_error
    assert "128 characters" in text(result)
    factory.assert_not_called()


@pytest.mark.parametrize(
    "status",
    ["active", "paused", "completed", "ACTIVE", "deleted", "future-value", "x" * 128],
)
def test_documented_campaign_statuses(monkeypatch, status):
    api = object.__new__(client.SmithAIClient)
    api.patch = Mock(return_value={"ok": True})
    monkeypatch.setattr(server, "_client", lambda: api)
    assert not invoke(
        "update_campaign", {"campaign_id": "probe", "status": status}
    ).is_error
    assert api.patch.call_args.kwargs["body"] == {"status": status}
