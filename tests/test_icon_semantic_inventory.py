from __future__ import annotations

from scripts.audit_icon_semantics import build_inventory


def test_icon_inventory_keeps_source_and_runtime_denominators_distinct() -> None:
    inventory = build_inventory()
    denominators = inventory["denominators"]

    assert inventory["baseline"]["warning"] == "Source call sites are not rendered DOM instances."
    assert denominators["unique_literal_glyph_names"] >= 70
    assert denominators["literal_interactive_source_call_sites"] >= 120
    assert denominators["literal_informational_source_call_sites"] >= 40
    assert denominators["dynamic_icon_expressions"] >= 30
    assert denominators["preview_story_sources"] == len(inventory["preview_story_pairs"])


def test_icon_inventory_rejects_known_semantic_falsehoods() -> None:
    inventory = build_inventory()
    pairs = {tuple(pair) for pair in inventory["preview_story_pairs"]}
    pairs.update(tuple(pair) for pair in inventory["persistent_pair_directions"])

    for rejected in (
        ("balance", "account_balance_wallet"),
        ("pause", "stop"),
        ("check_circle_outline", "gpp_maybe"),
        ("gpp_maybe", "cloud_off"),
        ("add_to_drive", "cloud_upload"),
    ):
        assert rejected not in pairs
