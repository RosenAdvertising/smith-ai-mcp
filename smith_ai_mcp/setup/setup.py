#!/usr/bin/env python3
"""
smith-ai-mcp setup — configure API key and verify connection.
"""

import sys

from smith_ai_mcp import credentials


def main():
    print("smith-ai-mcp setup")
    print("=" * 40)
    print()
    print("Get your API key at: smith.ai → Dashboard → Settings → API")
    print()

    existing_key = credentials.get_secret("SMITH_API_KEY")

    if existing_key:
        masked = (
            existing_key[:4] + "..." + existing_key[-4:]
            if len(existing_key) > 8
            else "****"
        )
        prompt = f"API key [{masked}] (press Enter to keep): "
    else:
        prompt = "Enter your Smith.ai API key: "

    try:
        api_key = input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled.")
        sys.exit(1)

    if not api_key:
        if existing_key:
            api_key = existing_key
            print("Keeping existing API key.")
        else:
            print("No API key provided. Exiting.")
            sys.exit(1)

    # Persist through the pluggable store (OS keyring by default).
    backend = credentials.set_secret("SMITH_API_KEY", api_key)
    if backend == "keyring":
        print(f"API key saved to the OS keyring ({credentials.storage_backend()}).")
    else:
        print(f"API key saved to {credentials.ENV_FILE} (0600).")
    print()

    # Run verify
    print("Verifying connection...")
    from smith_ai_mcp.setup.verify import main as verify_main

    verify_main()


if __name__ == "__main__":
    main()
