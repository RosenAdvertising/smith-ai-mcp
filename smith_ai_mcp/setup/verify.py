import sys


def main():
    try:
        from smith_ai_mcp.client import SmithAIClient

        client = SmithAIClient()
        connected = False
        try:
            client.get_account()
            connected = True
        except RuntimeError as e:
            msg = str(e)
            if not any(code in msg for code in ("400", "404", "405")):
                raise
        if not connected:
            try:
                client.list_calls(limit=1)
                connected = True
            except Exception as exc:
                raise RuntimeError("Smith.ai verification failed") from exc
        print("Connected to Smith.ai.")
        print("smith-ai-mcp is ready.")
    except Exception:  # noqa: BLE001 - final CLI boundary exits safely
        print("Error: Smith.ai verification failed.")
        print("Run smith-ai-mcp-setup to configure your API key.")
        sys.exit(1)


if __name__ == "__main__":
    main()
