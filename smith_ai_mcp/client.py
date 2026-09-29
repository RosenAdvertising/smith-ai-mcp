import logging
import os
import sys
import time

import requests

from smith_ai_mcp import credentials

BASE_URL = "https://api.smith.ai"
logger = logging.getLogger(__name__)


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
    pass


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
        value = int(resp.headers.get("Retry-After", default))
        return value if 0 <= value <= 3600 else default
    except (TypeError, ValueError):
        return default


def _json_response(resp):
    try:
        return resp.json()
    except ValueError as exc:
        logger.warning(
            "smith_api_response_rejected",
            extra={"reason": "non_json", "status": resp.status_code},
        )
        raise RuntimeError(
            f"Smith.ai API returned a non-JSON response ({resp.status_code})"
        ) from exc


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

    def _request(self, method, path, params=None, json_body=None, _rate_retries=0):
        url = f"{BASE_URL}/{path.lstrip('/')}"
        resp = self.session.request(method, url, params=params, json=json_body)
        if resp.status_code == 401:
            logger.warning(
                "smith_api_request_rejected",
                extra={"reason": "invalid_api_key", "status": 401},
            )
            raise AuthenticationError("authentication_rejected")
        if resp.status_code == 429 and _rate_retries < 3:
            wait = _retry_after_seconds(resp)
            print(f"Rate limited. Waiting {wait}s...", file=sys.stderr)
            time.sleep(wait)
            return self._request(
                method,
                path,
                params=params,
                json_body=json_body,
                _rate_retries=_rate_retries + 1,
            )
        if resp.status_code == 429:
            raise RateLimitError(_retry_after_seconds(resp))
        if resp.status_code == 404:
            raise NotFoundError("not_found")
        if resp.status_code == 204:
            return {"success": True}
        if not resp.ok:
            logger.warning(
                "smith_api_request_rejected",
                extra={"reason": "upstream_error", "status": resp.status_code},
            )
            safe_reasons = {
                400: "request rejected",
                403: "access denied",
                409: "conflict",
                422: "request rejected",
                500: "service unavailable",
                502: "service unavailable",
                503: "service unavailable",
                504: "service unavailable",
            }
            raise VendorHTTPError(
                resp.status_code, safe_reasons.get(resp.status_code, "request failed")
            )
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
        return self.get(f"/calls/{call_id}")

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
        return self.get(f"/campaigns/{campaign_id}")

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
        body = {}
        if name:
            body["name"] = name
        if script:
            body["script"] = script
        if status:
            body["status"] = status
        return self.patch(f"/campaigns/{campaign_id}", body=body)

    def get_campaign_stats(self, campaign_id):
        return self.get(f"/campaigns/{campaign_id}/stats")
