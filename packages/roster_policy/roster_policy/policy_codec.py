"""Strict, deterministic documents for prelaunch weekly policy revisions.

Only settings are serialized. Identity, revision, commands, approvals, people
and published service totals belong to their owning modules, not this codec.
"""

from __future__ import annotations

import json

from .configurable import (
    BusinessId, BusinessSettings, ConfigurationError, DutyTimes, TimeWindow, WeeklyPolicy,
)


def encode_weekly_policy(policy: WeeklyPolicy) -> str:
    """Encode validated settings with one stable representation for fingerprints."""
    if not isinstance(policy, WeeklyPolicy):
        raise ConfigurationError("Only a WeeklyPolicy can be encoded as weekly settings.")
    document = {
        "schemaVersion": 1,
        "mode": "weekly",
        "businesses": [
            {
                "business": post.business.value,
                "room": post.room,
                "capacity": post.capacity,
                "enabled": post.enabled,
                "open_weekdays": list(post.open_weekdays),
                "opening": {"start": post.times.opening.start, "end": post.times.opening.end},
                "service": {"start": post.times.service.start, "end": post.times.service.end},
                "linked": post.times.linked,
            }
            for post in policy.businesses
        ],
    }
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigurationError("Policy documents must not contain duplicate fields.")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> object:
    raise ConfigurationError("Policy documents must use finite JSON values.")


def _fields(value: object, expected: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != expected:
        raise ConfigurationError("Policy documents require exactly the supported fields.")
    return value


def _window(value: object) -> TimeWindow:
    raw = _fields(value, {"start", "end"})
    return TimeWindow(raw["start"], raw["end"])


def decode_weekly_policy(document: str) -> WeeklyPolicy:
    """Validate every stored field, then reuse the canonical policy invariants.

    Unknown schemas/fields, malformed data and ambiguous duplicate keys fail
    explicitly. A failed read must never replace persisted settings with defaults.
    """
    if not isinstance(document, str):
        raise ConfigurationError("A policy document must be JSON text.")
    try:
        raw = json.loads(document, object_pairs_hook=_unique_object, parse_constant=_reject_nonfinite)
    except (ValueError, RecursionError) as error:
        raise ConfigurationError("The policy document is not valid supported JSON.") from error
    raw = _fields(raw, {"schemaVersion", "mode", "businesses"})
    if type(raw["schemaVersion"]) is not int or raw["schemaVersion"] != 1 or raw["mode"] != "weekly":
        raise ConfigurationError("The policy document schema or mode is not supported.")
    if type(raw["businesses"]) is not list:
        raise ConfigurationError("Business settings must be an explicit list.")
    posts = []
    for value in raw["businesses"]:
        post = _fields(value, {
            "business", "room", "capacity", "enabled", "open_weekdays", "opening", "service", "linked",
        })
        if type(post["open_weekdays"]) is not list:
            raise ConfigurationError("Ordinary open weekdays must be an explicit list.")
        try:
            business = BusinessId(post["business"])
        except (ValueError, TypeError) as error:
            raise ConfigurationError("The policy document has an unknown business identity.") from error
        posts.append(BusinessSettings(
            business=business,
            room=post["room"],
            capacity=post["capacity"],
            times=DutyTimes(_window(post["opening"]), _window(post["service"]), linked=post["linked"]),
            enabled=post["enabled"],
            open_weekdays=post["open_weekdays"],
        ))
    return WeeklyPolicy(tuple(posts))
