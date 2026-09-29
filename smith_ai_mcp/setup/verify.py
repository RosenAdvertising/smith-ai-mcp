import sys

from smith_ai_mcp.client import (
    ACCESS_DENIED_MESSAGE,
    AuthenticationError,
    MissingCredentialsError,
    NotFoundError,
    VendorHTTPError,
)


def main():
    try:
        from smith_ai_mcp.client import SmithAIClient

        client = SmithAIClient()
        connected = False
        try:
            client.get_account()
            connected = True
        except (NotFoundError, VendorHTTPError) as exc:
            if exc.status not in (400, 404, 405):
                raise
        if not connected:
            client.list_calls(limit=1)
        print("Connected to Smith.ai.")
        print("smith-ai-mcp is ready.")
    except (MissingCredentialsError, AuthenticationError, VendorHTTPError) as exc:
        if isinstance(exc, VendorHTTPError) and exc.status == 403:
            message = ACCESS_DENIED_MESSAGE
        elif isinstance(exc, MissingCredentialsError):
            message = "Missing SMITH_API_KEY. Run smith-ai-mcp-setup and restart the MCP server."
        else:
            message = "Smith.ai verification failed. Check your API key and re-run smith-ai-mcp-setup."
        print(f"Error: {message}")
        sys.exit(1)
    except Exception:  # noqa: BLE001 - final CLI boundary exits safely
        print("Error: Smith.ai verification failed.")
        print("Run smith-ai-mcp-setup to configure your API key.")
        sys.exit(1)


if __name__ == "__main__":
    main()
