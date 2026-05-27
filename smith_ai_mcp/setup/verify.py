#!/usr/bin/env python3
import sys


def main():
    try:
        from smith_ai_mcp.client import SmithAIClient

        client = SmithAIClient()
        connected = False
        try:
            info = client.get_account()
            connected = True
            if isinstance(info, dict):
                name = (
                    info.get("name")
                    or info.get("account_name")
                    or info.get("email", "")
                )
                if name:
                    print(f"Account: {name}")
        except RuntimeError as e:
            msg = str(e)
            if not any(code in msg for code in ("400", "404", "405")):
                raise
        if not connected:
            try:
                client.list_calls(limit=1)
                connected = True
            except Exception as e2:
                raise RuntimeError(str(e2))
        print("Connected to Smith.ai.")
        print("smith-ai-mcp is ready.")
    except Exception as e:
        print(f"Error: {e}")
        print("Run smith-ai-mcp-setup to configure your API key.")
        sys.exit(1)


if __name__ == "__main__":
    main()
