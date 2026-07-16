"""Generate or verify the executable Sing Yin design-token contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.ui.design_token_contract import (
    validate_design_token_contract,
    write_generated_files,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify NiceGUI and Cloudflare design-token artifacts."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed outputs and runtime alignment without writing files.",
    )
    args = parser.parse_args()

    if not args.check:
        write_generated_files()

    drift = validate_design_token_contract()
    if drift:
        for problem in drift:
            print(f"ERROR: {problem}")
        return 1
    print("Design-token contract is current and runtime-aligned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
