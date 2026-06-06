#!/usr/bin/env python3
"""
smith-ai-mcp setup — configure API key and verify connection.
"""

import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".smith-ai-mcp"
ENV_FILE = CONFIG_DIR / ".env"


def main():
    print("smith-ai-mcp setup")
    print("=" * 40)
    print()
    print("Get your API key at: smith.ai → Dashboard → Settings → API")
    print()

    existing_key = ""
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("SMITH_API_KEY="):
                    existing_key = line.split("=", 1)[1].strip()
                    break

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

    # Save to config dir
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(0o700)
    # Credentials are stored in a chmod-0600 file. A pluggable OS-keyring backend
    # (macOS Keychain / Windows Credential Manager / Linux Secret Service) is being
    # evaluated as optional hardening; see the "pluggable OS-keyring" MCP task.
    with open(ENV_FILE, "w") as f:
        f.write(f"SMITH_API_KEY={api_key}\n")
    os.chmod(ENV_FILE, 0o600)
    print(f"API key saved to {ENV_FILE}")
    print()

    # Run verify
    print("Verifying connection...")
    from smith_ai_mcp.setup.verify import main as verify_main

    verify_main()


if __name__ == "__main__":
    main()
