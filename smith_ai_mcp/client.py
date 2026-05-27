#!/usr/bin/env python3
import os
import sys
import time
import requests
from pathlib import Path

BASE_URL = "https://api.smith.ai"
CONFIG_DIR = Path.home() / ".smith-ai-mcp"


def _load_env():
    env_file = CONFIG_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


_load_env()


def _retry_after_seconds(resp, default=10):
    try:
        return int(resp.headers.get("Retry-After", default))
    except (TypeError, ValueError):
        return default


def _json_response(resp):
    try:
        return resp.json()
    except ValueError:
        raise RuntimeError(
            f"Smith.ai API returned non-JSON ({resp.status_code}): {resp.text[:200]}"
        )


# Endpoints based on docs.smith.ai — verify paths before production use. Smith.ai docs are thin.
class SmithAIClient:
    def __init__(self):
        api_key = os.environ.get("SMITH_API_KEY", "")
        if not api_key:
            raise RuntimeError("No Smith.ai API key found. Run: smith-ai-mcp-setup")
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
            raise RuntimeError("Smith.ai API key invalid. Run: smith-ai-mcp-setup")
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
        if resp.status_code == 204:
            return {"success": True}
        if not resp.ok:
            raise RuntimeError(
                f"Smith.ai API error {resp.status_code}: {resp.text[:400]}"
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
        params = {"page": page, "limit": limit}
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
            raise ValueError("contacts must be a list")
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
