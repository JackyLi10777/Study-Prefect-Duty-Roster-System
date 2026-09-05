"""Versioned policy documents are validated data, never a second rule engine."""

from dataclasses import replace
import json

import pytest

from roster_policy.configurable import (
    ConfigurationError, DutyTimes, TimeWindow, default_cp_policy, default_weekly_policy,
)
from roster_policy.policy_codec import decode_weekly_policy, encode_weekly_policy


def test_default_round_trip_is_canonical_and_contains_no_derived_minutes():
    policy = default_weekly_policy()
    encoded = encode_weekly_policy(policy)
    assert decode_weekly_policy(encoded) == policy
    assert encode_weekly_policy(decode_weekly_policy(encoded)) == encoded
    raw = json.loads(encoded)
    assert raw["schemaVersion"] == 1
    assert raw["mode"] == "weekly"
    assert len(raw["businesses"]) == 4
    assert "minutes" not in encoded
    assert "revision" not in raw
    assert "407" in encoded and "406" in encoded


def test_custom_room_capacity_f1_and_independent_service_time_survive_reload():
    policy = default_weekly_policy()
    posts = list(policy.businesses)
    posts[1] = replace(posts[1], room="溫習室 509", capacity=3,
                       times=DutyTimes(TimeWindow("08:30", "12:00"),
                                       TimeWindow("09:00", "10:07"), linked=False))
    posts[3] = replace(posts[3], enabled=True, open_weekdays=(1, 4))
    custom = replace(policy, businesses=posts)
    reloaded = decode_weekly_policy(encode_weekly_policy(custom))
    assert reloaded == custom
    assert reloaded.businesses[1].times.service.minutes == 67
    assert reloaded.businesses[3].enabled is True
    assert reloaded.businesses[3].open_weekdays == (1, 4)
    assert policy == default_weekly_policy()


@pytest.mark.parametrize("value", ["", "{", "null", "[]", "true", "1", None, b"{}"])
def test_malformed_or_non_document_inputs_fail_without_default_fallback(value):
    with pytest.raises(ConfigurationError):
        decode_weekly_policy(value)


@pytest.mark.parametrize("version", [True, 0, 2, 1.0, "1", None])
def test_unknown_or_non_integer_schema_versions_fail(version):
    raw = json.loads(encode_weekly_policy(default_weekly_policy()))
    raw["schemaVersion"] = version
    with pytest.raises(ConfigurationError):
        decode_weekly_policy(json.dumps(raw))


@pytest.mark.parametrize("mutation", [
    lambda raw: raw.update(mode="cp"),
    lambda raw: raw.update(unrecognized="ignore me"),
    lambda raw: raw.pop("businesses"),
    lambda raw: raw.update(businesses={}),
    lambda raw: raw["businesses"].pop(),
    lambda raw: raw["businesses"].append(raw["businesses"][0].copy()),
    lambda raw: raw["businesses"][1].update(capacity=True),
    lambda raw: raw["businesses"][1].update(capacity=21),
    lambda raw: raw["businesses"][1].update(capacity=float("nan")),
    lambda raw: raw["businesses"][1].update(enabled="false"),
    lambda raw: raw["businesses"][1].update(linked=1),
    lambda raw: raw["businesses"][1].update(business="Room 407"),
    lambda raw: raw["businesses"][1].update(business="cp_form_1"),
    lambda raw: raw["businesses"][1].update(room=None),
    lambda raw: raw["businesses"][1].update(room="407\u2028408"),
    lambda raw: raw["businesses"][1].update(open_weekdays={}),
    lambda raw: raw["businesses"][1].update(open_weekdays=[5]),
    lambda raw: raw["businesses"][1].update(open_weekdays=[0, 0]),
    lambda raw: raw["businesses"][1].update(extra="ignore me"),
    lambda raw: raw["businesses"][1].pop("room"),
    lambda raw: raw["businesses"][1]["opening"].update(minutes=80),
    lambda raw: raw["businesses"][1]["service"].update(start="15:40:00"),
    lambda raw: raw["businesses"][1]["service"].update(end="16:30"),
])
def test_invalid_documents_cannot_bypass_policy_invariants(mutation):
    raw = json.loads(encode_weekly_policy(default_weekly_policy()))
    mutation(raw)
    with pytest.raises(ConfigurationError):
        decode_weekly_policy(json.dumps(raw))


@pytest.mark.parametrize("target", ["root", "business", "window"])
def test_duplicate_object_keys_are_rejected_instead_of_last_value_winning(target):
    encoded = encode_weekly_policy(default_weekly_policy())
    if target == "root":
        encoded = encoded.replace('"schemaVersion":1', '"schemaVersion":2,"schemaVersion":1')
    elif target == "business":
        encoded = encoded.replace('"capacity":1', '"capacity":99,"capacity":1', 1)
    else:
        encoded = encoded.replace('"start":"15:40"', '"start":"00:00","start":"15:40"', 1)
    with pytest.raises(ConfigurationError):
        decode_weekly_policy(encoded)


def test_reordered_fields_and_businesses_normalize_to_one_digest_input():
    policy = default_weekly_policy()
    canonical = encode_weekly_policy(policy)
    raw = json.loads(canonical)
    raw["businesses"].reverse()
    raw = dict(reversed(list(raw.items())))
    assert encode_weekly_policy(decode_weekly_policy(json.dumps(raw, indent=2))) == canonical


def test_cp_policy_is_not_silently_written_as_a_weekly_policy():
    with pytest.raises(ConfigurationError):
        encode_weekly_policy(default_cp_policy(f1_room="501", f2_room="502", f3_room="503"))


@pytest.mark.parametrize("surrogate", ["\ud800", "\udfff"])
def test_lone_surrogates_fail_before_digest_or_sqlite_encoding(surrogate):
    policy = default_weekly_policy()
    with pytest.raises(ConfigurationError):
        posts = list(policy.businesses)
        posts[1] = replace(posts[1], room="Rm " + surrogate)
        encode_weekly_policy(replace(policy, businesses=posts))
    raw = json.loads(encode_weekly_policy(policy))
    raw["businesses"][1]["room"] = "Rm " + surrogate
    with pytest.raises(ConfigurationError):
        decode_weekly_policy(json.dumps(raw))


def test_valid_non_bmp_unicode_remains_utf8_serializable():
    policy = default_weekly_policy()
    posts = list(policy.businesses)
    posts[1] = replace(posts[1], room="Rm 509 \U00020000")
    custom = replace(policy, businesses=posts)
    encoded = encode_weekly_policy(custom)
    assert decode_weekly_policy(encoded.encode("utf-8").decode("utf-8")) == custom
