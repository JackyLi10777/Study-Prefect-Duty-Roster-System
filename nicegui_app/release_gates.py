"""Source-owned release checklist, shared by report writers and all consumers.

This contract covers the existing runner. Further mobile/Public/Viewer gates
must be added with their producers; this is not the complete prelaunch matrix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

GATE_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "scripts" / "release-gates.json"


def read_strict_json(path: Path) -> object:
    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field.")
            result[key] = value
        return result

    def reject_constant(_value):
        raise ValueError("Invalid JSON constant.")

    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields,
                          parse_constant=reject_constant)
    except (RecursionError, UnicodeError) as error:
        raise ValueError("Invalid JSON document.") from error


def load_gate_manifest(path: Path = GATE_MANIFEST_PATH) -> dict[str, object]:
    payload = read_strict_json(path)
    if not isinstance(payload, dict) or set(payload) != {"schemaVersion", "reportSchemaVersion", "requiredChecks"}:
        raise ValueError("Invalid release gate manifest shape.")
    names = payload["requiredChecks"]
    if (type(payload["schemaVersion"]) is not int or payload["schemaVersion"] != 1
            or type(payload["reportSchemaVersion"]) is not int or payload["reportSchemaVersion"] != 4
            or not isinstance(names, list) or not names
            or any(not isinstance(name, str) or re.fullmatch(r"[a-z][a-z0-9_]*", name) is None for name in names)
            or len(set(names)) != len(names)):
        raise ValueError("Invalid release gate manifest identities or version.")
    return payload


_MANIFEST = load_gate_manifest()
RELEASE_REPORT_SCHEMA_VERSION = _MANIFEST["reportSchemaVersion"]
REQUIRED_CHECK_IDENTITIES = tuple(_MANIFEST["requiredChecks"])
GATE_MANIFEST_BINDING = {
    "version": _MANIFEST["schemaVersion"],
    # Canonical JSON binds meaning, independent of Windows checkout newlines.
    "fingerprint": hashlib.sha256(json.dumps(_MANIFEST, sort_keys=True, separators=(",", ":"),
                                              ensure_ascii=True).encode("utf-8")).hexdigest(),
}


def validate_gate_declaration(payload: object) -> None:
    if (not isinstance(payload, dict)
            or type(payload.get("schemaVersion")) is not int
            or payload.get("schemaVersion") != RELEASE_REPORT_SCHEMA_VERSION
            or payload.get("gateManifest") != GATE_MANIFEST_BINDING
            or not isinstance(payload.get("gateManifest"), dict)
            or type(payload["gateManifest"].get("version")) is not int
            or payload.get("requiredCheckIdentities") != list(REQUIRED_CHECK_IDENTITIES)):
        raise ValueError("Release check declaration does not match the source contract.")


def validate_completed_gates(payload: object) -> None:
    validate_gate_declaration(payload)
    checks = payload.get("checks")
    if (not isinstance(checks, list) or any(not isinstance(check, dict) for check in checks)
            or [check.get("name") for check in checks] != list(REQUIRED_CHECK_IDENTITIES)):
        raise ValueError("Executed release checks do not match the source contract.")
    if any(check.get("status") != "pass" or type(check.get("durationMs")) is not int
           or check["durationMs"] < 0 for check in checks):
        raise ValueError("Not every required release check has successful timing evidence.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source-owned release gate evidence; no deployment.")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = read_strict_json(args.report)
        validate_completed_gates(report)
    except (OSError, ValueError):
        print("Release gate evidence is invalid.")
        return 1
    print(json.dumps({"reportSchemaVersion": RELEASE_REPORT_SCHEMA_VERSION,
                      "requiredChecks": REQUIRED_CHECK_IDENTITIES, "gateManifest": GATE_MANIFEST_BINDING,
                      "report": report}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
