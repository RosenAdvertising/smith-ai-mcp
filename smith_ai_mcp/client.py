import logging
import math
import os
import re
import time
from urllib.parse import quote

import requests

from smith_ai_mcp import credentials

BASE_URL = "https://api.smith.ai"
logger = logging.getLogger(__name__)
ACCESS_DENIED_MESSAGE = (
    "Smith.ai access denied: the connected account lacks permission for this action "
    "(or the authorization expired; re-run smith-ai-mcp-setup if so)."
)


def _path_id(value, parameter: str) -> str:
    """Validate a plain identifier before URL quoting or any HTTP request."""
    expected = (
        "a non-empty plain identifier (ASCII letters, digits, -, _, ., ~); not . or .."
    )
    if (
        isinstance(value, bool)
        or not isinstance(value, (str, int))
        or str(value) in {".", ".."}
        or re.fullmatch(r"[A-Za-z0-9._~-]+", str(value)) is None
    ):
        raise ArgumentValidationError(parameter, expected)
    return quote(str(value), safe="")


class MissingCredentialsError(RuntimeError):
    pass


class AuthenticationError(RuntimeError):
    pass


class VendorHTTPError(RuntimeError):
    def __init__(self, status: int, reason: str):
        self.status = status
        self.reason = reason
        super().__init__(reason)


class RateLimitError(RuntimeError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("rate_limited")


class NotFoundError(RuntimeError):
    def __init__(self, status: int = 404):
        self.status = status
        super().__init__("not_found")


class TransportError(RuntimeError):
    def __init__(self, method: str):
        self.method = method.upper()
        if self.method == "GET":
            message = "Smith.ai could not be reached. Check connectivity and retry."
        else:
            message = (
                "Smith.ai could not be reached while submitting this change; the "
                "outcome is unknown. Check whether it completed before retrying."
            )
        super().__init__(message)


class ArgumentValidationError(ValueError):
    def __init__(self, field: str, expected: str):
        self.field = field
        self.expected = expected
        super().__init__(field)


class ContactsValidationError(TypeError):
    field = "contacts"
    expected = "an array of contact objects"


# Resolve credentials through the pluggable store (OS keyring -> .env file).
credentials.load_into_environ(["SMITH_API_KEY"])


def _retry_after_seconds(resp, default=10):
    try:
        value = float(resp.headers.get("Retry-After", default))
        if math.isfinite(value) and value >= 1:
            return math.ceil(value)
    except (TypeError, ValueError, OverflowError):
        pass
    return default


_SAFE_HTTP_REASONS = {
    400: "request rejected",
    409: "conflict",
    422: "request rejected",
    500: "service unavailable",
    502: "service unavailable",
    503: "service unavailable",
    504: "service unavailable",
}
_SAFE_VENDOR_REASONS = {
    "invalid_request": "invalid request",
    "validation_error": "validation failed",
    "invalid_parameter": "invalid parameter",
    "conflict": "conflict",
    "service_unavailable": "service unavailable",
    "service unavailable": "service unavailable",
}


def _vendor_reason(response):
    """Only fixed, recognized vendor codes may contribute to public messages."""
    fallback = _SAFE_HTTP_REASONS.get(response.status_code, "request failed")
    try:
        data = response.json()
    except ValueError:
        return fallback
    if not isinstance(data, dict):
        return fallback
    for source in (data, data.get("error")):
        if isinstance(source, dict):
            for key in ("code", "error_code", "error", "message", "detail"):
                value = source.get(key)
                if isinstance(value, str) and value.lower() in _SAFE_VENDOR_REASONS:
                    return _SAFE_VENDOR_REASONS[value.lower()]
    return fallback


def _json_response(resp):
    try:
        return resp.json()
    except ValueError:
        logger.warning(
            "smith_api_response_rejected",
            extra={"reason": "non_json", "status": resp.status_code},
        )
        raise VendorHTTPError(resp.status_code, "invalid JSON response") from None


# Endpoints based on docs.smith.ai — verify paths before production use. Smith.ai docs are thin.
class SmithAIClient:
    def __init__(self):
        api_key = os.environ.get("SMITH_API_KEY", "")
        if not api_key:
            logger.warning(
                "smith_api_request_rejected", extra={"reason": "missing_api_key"}
            )
            raise MissingCredentialsError("SMITH_API_KEY")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _request(
        self, method, path, params=None, json_body=None, _rate_retries=0, _retry_sleep=0
    ):
        url = f"{BASE_URL}/{path.lstrip('/')}"
        try:
            resp = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                timeout=30,
                allow_redirects=False,
            )
        except (requests.Timeout, requests.ConnectionError):
            logger.warning(
                "smith_api_request_failed",
                extra={"reason": "transport_error", "method": method.upper()},
            )
            raise TransportError(method) from None
        if resp.status_code == 401:
            logger.warning(
                "smith_api_request_rejected",
                extra={"reason": "unauthorized", "status": resp.status_code},
            )
            raise AuthenticationError("authentication_rejected")
        if resp.status_code == 403:
            logger.warning(
                "smith_api_request_rejected",
                extra={"reason": "access_denied", "status": resp.status_code},
            )
            raise VendorHTTPError(403, ACCESS_DENIED_MESSAGE)
        if resp.status_code == 429 and _rate_retries < 3:
            wait = _retry_after_seconds(resp)
            if _retry_sleep + wait > 60:
                raise RateLimitError(wait)
            time.sleep(wait)
            return self._request(
                method,
                path,
                params=params,
                json_body=json_body,
                _rate_retries=_rate_retries + 1,
                _retry_sleep=_retry_sleep + wait,
            )
        if resp.status_code == 429:
            raise RateLimitError(_retry_after_seconds(resp))
        if resp.status_code == 404:
            raise NotFoundError(resp.status_code)
        if 300 <= resp.status_code < 400:
            logger.warning(
                "smith_api_request_rejected",
                extra={"reason": "redirect_rejected", "status": resp.status_code},
            )
            raise VendorHTTPError(resp.status_code, "redirect rejected")
        if resp.status_code == 204:
            return {"success": True}
        if not resp.ok:
            logger.warning(
                "smith_api_request_rejected",
                extra={"reason": "upstream_error", "status": resp.status_code},
            )
            raise VendorHTTPError(resp.status_code, _vendor_reason(resp))
        return _json_response(resp)

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, body=None):
        return self._request("POST", path, json_body=body)

    def patch(self, path, body=None):
        return self._request("PATCH", path, json_body=body)

    # Account
    def get_account(self):
        return self.get("/account")

    # Calls
    def list_calls(self, page=1, limit=25, date_from="", date_to=""):
        params: dict[str, int | str] = {"page": page, "limit": limit}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self.get("/calls", params=params)

    def get_call(self, call_id):
        return self.get(f"/calls/{_path_id(call_id, 'call_id')}")

    def request_outbound_call(
        self, contact_name, phone_number, instructions="", priority="normal"
    ):
        body = {
            "contact_name": contact_name,
            "phone_number": phone_number,
            "priority": priority,
        }
        if instructions:
            body["instructions"] = instructions
        return self.post("/calls/outbound", body=body)

    # Campaigns
    def list_campaigns(self, page=1, limit=25):
        return self.get("/campaigns", params={"page": page, "limit": limit})

    def get_campaign(self, campaign_id):
        return self.get(f"/campaigns/{_path_id(campaign_id, 'campaign_id')}")

    def create_campaign(self, name, script, contacts):
        if not isinstance(contacts, list):
            logger.warning(
                "tool_input_rejected",
                extra={"field": "contacts", "reason": "invalid_type"},
            )
            raise ContactsValidationError("contacts must be an array")
        return self.post(
            "/campaigns", body={"name": name, "script": script, "contacts": contacts}
        )

    def update_campaign(self, campaign_id, name="", script="", status=""):
        path = f"/campaigns/{_path_id(campaign_id, 'campaign_id')}"
        validate_campaign_update(name, script, status)
        body = {}
        if name:
            body["name"] = name
        if script:
            body["script"] = script
        if status:
            body["status"] = status
        return self.patch(path, body=body)

    def get_campaign_stats(self, campaign_id):
        return self.get(f"/campaigns/{_path_id(campaign_id, 'campaign_id')}/stats")


def validate_campaign_update(name, script, status):
    if not any(value.strip() for value in (name, script, status)):
        raise ArgumentValidationError(
            "update", "at least one non-empty name, script, or status"
        )
    if status and (
        not status.strip()
        or len(status) > 128
        or any(ord(char) < 32 or ord(char) == 127 for char in status)
    ):
        raise ArgumentValidationError(
            "status", "a non-empty string of at most 128 characters without controls"
        )
