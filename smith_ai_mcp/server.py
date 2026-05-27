#!/usr/bin/env python3
"""
Smith.ai MCP server.

Smith.ai human+AI hybrid receptionist integration: request outbound calls
(Smith places calls via their receptionist team), manage outreach campaigns,
retrieve call records. Note: Smith.ai uses human receptionists + AI, not a
configurable voice agent.
"""

from mcp.server.fastmcp import FastMCP
from smith_ai_mcp.client import SmithAIClient

mcp = FastMCP(
    "smith-ai",
    instructions=(
        "Smith.ai human+AI hybrid receptionist integration: request outbound calls "
        "(Smith places calls via their receptionist team), manage outreach campaigns, "
        "retrieve call records. Note: Smith.ai uses human receptionists + AI, not a "
        "configurable voice agent."
    ),
)


def _client():
    return SmithAIClient()


@mcp.tool()
def get_account() -> dict:
    """Retrieve Smith.ai account information and settings."""
    return _client().get_account()


@mcp.tool()
def list_calls(
    page: int = 1, limit: int = 25, date_from: str = "", date_to: str = ""
) -> dict:
    """
    List call records from Smith.ai.

    Args:
        page: Page number (default 1).
        limit: Records per page (default 25, max typically 100).
        date_from: Start date filter in YYYY-MM-DD format (optional).
        date_to: End date filter in YYYY-MM-DD format (optional).
    """
    return _client().list_calls(
        page=page, limit=limit, date_from=date_from, date_to=date_to
    )


@mcp.tool()
def get_call(call_id: str) -> dict:
    """
    Retrieve a single call record by ID.

    Args:
        call_id: The Smith.ai call identifier.
    """
    return _client().get_call(call_id)


@mcp.tool()
def request_outbound_call(
    contact_name: str,
    phone_number: str,
    instructions: str = "",
    priority: str = "normal",
) -> dict:
    """
    Request Smith.ai to place an outbound call on your behalf. Smith's receptionist team handles the call.

    Args:
        contact_name: Full name of the contact to call.
        phone_number: Phone number to call (E.164 format recommended, e.g. +15551234567).
        instructions: Optional instructions for the receptionist (e.g. purpose of the call, key points to cover).
        priority: Call priority — 'normal' or 'urgent' (default: 'normal').
    """
    return _client().request_outbound_call(
        contact_name=contact_name,
        phone_number=phone_number,
        instructions=instructions,
        priority=priority,
    )


@mcp.tool()
def list_campaigns(page: int = 1, limit: int = 25) -> dict:
    """
    List outbound call campaigns.

    Args:
        page: Page number (default 1).
        limit: Records per page (default 25).
    """
    return _client().list_campaigns(page=page, limit=limit)


@mcp.tool()
def get_campaign(campaign_id: str) -> dict:
    """
    Retrieve details for a single campaign.

    Args:
        campaign_id: The Smith.ai campaign identifier.
    """
    return _client().get_campaign(campaign_id)


@mcp.tool()
def create_campaign(name: str, script: str, contacts: list) -> dict:
    """
    Create a new outbound call campaign.

    Args:
        name: Campaign name.
        script: Script or instructions the receptionist team will follow for each call.
        contacts: Array of contact objects, e.g. [{"name": "Jane Doe", "phone": "+15551234567"}].
    """
    return _client().create_campaign(name=name, script=script, contacts=contacts)


@mcp.tool()
def update_campaign(
    campaign_id: str,
    name: str = "",
    script: str = "",
    status: str = "",
) -> dict:
    """
    Update an existing campaign. Only fields provided (non-empty) will be updated.

    Args:
        campaign_id: The Smith.ai campaign identifier.
        name: New campaign name (optional).
        script: Updated script/instructions (optional).
        status: New status, e.g. 'active', 'paused', 'completed' (optional).
    """
    return _client().update_campaign(
        campaign_id=campaign_id,
        name=name,
        script=script,
        status=status,
    )


@mcp.tool()
def get_campaign_stats(campaign_id: str) -> dict:
    """
    Retrieve performance statistics for a campaign (calls made, completed, outcomes, etc.).

    Args:
        campaign_id: The Smith.ai campaign identifier.
    """
    return _client().get_campaign_stats(campaign_id)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
