"""Compatibility entrypoint for the unified Guest browser verifier.

The former static ``/guest`` and ``/try`` products have been retired.  Keep
this filename so operator scripts and release fingerprints fail forward into
the real NiceGUI Guest workbench verification instead of silently exercising
an obsolete second product.
"""

from __future__ import annotations

if __package__:
    from scripts.verify_unified_guest_ui import main
else:  # pragma: no cover - exercised when invoked as a script
    from verify_unified_guest_ui import main


if __name__ == "__main__":
    raise SystemExit(main())
