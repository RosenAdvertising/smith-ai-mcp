"""Fail when the locked MCP SDK drifts from the migrated specification."""

from __future__ import annotations

import argparse

from mcp.types import LATEST_PROTOCOL_VERSION
from mcp_types.version import MODERN_PROTOCOL_VERSIONS

EXPECTED_MCP_PROTOCOL_VERSION = "2026-07-28"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mcp-only",
        action="store_true",
        help="check only the installed MCP protocol revision",
    )
    parser.parse_args()

    matches = (
        LATEST_PROTOCOL_VERSION == EXPECTED_MCP_PROTOCOL_VERSION
        and MODERN_PROTOCOL_VERSIONS == (EXPECTED_MCP_PROTOCOL_VERSION,)
    )
    print(f"Spec check: {'PASS' if matches else 'FAIL'}")
    if not matches:
        print(f"Expected: {EXPECTED_MCP_PROTOCOL_VERSION}")
        print(f"Latest: {LATEST_PROTOCOL_VERSION}")
        print(f"Modern: {MODERN_PROTOCOL_VERSIONS}")
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
