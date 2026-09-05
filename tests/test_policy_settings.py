from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from threading import Barrier

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError

from nicegui_app.services.sqlite_policy_repository import SQLitePolicyRepository
from roster_core.policy_settings import (
    MemoryPolicyRepository,
    PolicyChange,
    PolicyCommandConflict,
    PolicyNotFound,
    PolicySettings,
    PolicySettingsError,
    PolicyStorageError,
    PolicyVersionConflict,
    ResetPreview,
    StoredPolicyRevision,
)
from roster_policy.configurable import (
    BusinessId,
    DutyTimes,
    TimeWindow,
    WeeklyPolicy,
    default_weekly_policy,
)
from roster_policy.policy_codec import encode_weekly_policy


YEAR = 2026


def custom_policy(room="509"):
    window = TimeWindow("15:40", "16:47")
    return WeeklyPolicy(tuple(
        replace(post, room=room, times=DutyTimes(window, window))
        if post.business is BusinessId.STUDY_ROOM
        else replace(post, enabled=True) if post.business is BusinessId.FORM_1_STUDY_GROUP
        else post
        for post in default_weekly_policy().businesses
    ))


@pytest.fixture
def sqlite_pair(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'policy-test.sqlite3'}")
    repository = SQLitePolicyRepository(engine)
    repository.create_schema()
    try:
        yield engine, repository
    finally:
        engine.dispose()


@pytest.fixture(params=["memory", "sqlite"])
def repository(request):
    return MemoryPolicyRepository() if request.param == "memory" else request.getfixturevalue("sqlite_pair")[1]


def test_custom_policy_survives_new_settings_instance_and_preserves_history(repository):
    settings = PolicySettings(repository)
    with pytest.raises(PolicyNotFound):
        settings.current(YEAR)
    original = settings.initialize(YEAR, command_id="init")
    saved = settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save")
    reopened = PolicySettings(repository)
    assert original.revision == 1
    assert saved.revision == 2
    assert reopened.current(YEAR) == saved
    assert reopened.revision(YEAR, 1) == original
    study = next(post for post in saved.policy.businesses if post.business is BusinessId.STUDY_ROOM)
    assert study.room == "509"
    assert study.times.service.minutes == 67
    assert next(post for post in saved.policy.businesses if post.business is BusinessId.FORM_1_STUDY_GROUP).enabled
    assert original.policy == default_weekly_policy()
    with pytest.raises(FrozenInstanceError):
        saved.revision = 999


def test_reset_preview_covers_all_fields_without_mutating_and_restores_new_revision(repository):
    settings = PolicySettings(repository)
    original = settings.initialize(YEAR, command_id="init")
    custom = custom_policy()
    custom = WeeklyPolicy(tuple(
        replace(post, capacity=3, enabled=False, open_weekdays=(1, 4), times=DutyTimes(
            TimeWindow("15:41", "17:01"), TimeWindow("15:40", "16:47"), linked=False,
        )) if post.business is BusinessId.STUDY_ROOM else post for post in custom.businesses
    ))
    saved = settings.save(YEAR, custom, expected_revision=1, command_id="save")
    preview = settings.preview_reset(YEAR)
    assert settings.current(YEAR) == saved
    assert preview.expected_revision == 2
    assert preview.target_policy == original.policy
    changes = {change.field: change for change in preview.changes if change.business is BusinessId.STUDY_ROOM}
    assert set(changes) == {"room", "capacity", "enabled", "weekdays", "opening", "service", "linked"}
    assert changes["room"].before == "509"
    assert changes["room"].after == "407"
    assert changes["service"].before.minutes == 67
    assert changes["service"].after.minutes == 80
    assert changes["linked"].before is False
    reset = settings.reset(preview, command_id="reset")
    assert reset.revision == 3
    assert reset.policy == default_weekly_policy()
    assert settings.revision(YEAR, 1) == original
    assert settings.revision(YEAR, 2) == saved
    with pytest.raises(FrozenInstanceError):
        preview.expected_revision = 99


def test_each_new_accepted_command_adds_a_revision_even_without_policy_difference(repository):
    settings = PolicySettings(repository)
    original = settings.initialize(YEAR, command_id="init")
    saved = settings.save(YEAR, original.policy, expected_revision=1, command_id="equal-save")
    assert saved.revision == 2
    preview = settings.preview_reset(YEAR)
    assert preview.changes == ()
    assert settings.reset(preview, command_id="equal-reset").revision == 3
    with pytest.raises(PolicyVersionConflict):
        settings.initialize(YEAR, command_id="new-init")
    assert settings.current(YEAR).revision == 3


def test_retries_return_original_committed_revision_after_later_edits(repository):
    settings = PolicySettings(repository)
    original = settings.initialize(YEAR, command_id="init")
    saved = settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save")
    preview = settings.preview_reset(YEAR)
    reset = settings.reset(preview, command_id="reset")
    latest = settings.save(YEAR, custom_policy("510"), expected_revision=3, command_id="later")
    assert settings.initialize(YEAR, command_id="init") == original
    assert settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save") == saved
    assert settings.reset(preview, command_id="reset") == reset
    assert settings.current(YEAR) == latest
    with pytest.raises(PolicyVersionConflict):
        settings.reset(preview, command_id="stale-reset")
    with pytest.raises(PolicyVersionConflict):
        settings.save(YEAR, custom_policy(), expected_revision=2, command_id="stale-save")
    assert settings.current(YEAR) == latest


@pytest.mark.parametrize("difference", ["policy", "year", "revision", "operation"])
def test_command_identity_binds_canonical_policy_year_revision_and_operation(repository, difference):
    settings = PolicySettings(repository)
    settings.initialize(YEAR, command_id="init")
    preview = settings.preview_reset(YEAR)
    original = settings.save(YEAR, default_weekly_policy(), expected_revision=1, command_id="same-command")
    with pytest.raises(PolicyCommandConflict):
        if difference == "operation":
            settings.reset(preview, command_id="same-command")
        else:
            settings.save(
                YEAR + 1 if difference == "year" else YEAR,
                custom_policy() if difference == "policy" else default_weekly_policy(),
                expected_revision=2 if difference == "revision" else 1, command_id="same-command",
            )
    assert settings.current(YEAR) == original


@pytest.mark.parametrize("tamper", ["changes", "target", "old-revision", "not-preview"])
def test_reset_requires_untampered_reviewed_preview_and_does_not_consume_failed_command(repository, tamper):
    settings = PolicySettings(repository)
    settings.initialize(YEAR, command_id="init")
    saved = settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save")
    preview = settings.preview_reset(YEAR)
    if tamper == "changes":
        supplied = replace(preview, changes=())
    elif tamper == "target":
        supplied = replace(preview, target_policy=custom_policy("700"))
    elif tamper == "old-revision":
        supplied = replace(preview, expected_revision=1)
    else:
        supplied = None
    with pytest.raises(PolicySettingsError):
        settings.reset(supplied, command_id="decision")
    assert settings.current(YEAR) == saved
    assert settings.reset(preview, command_id="decision").revision == 3


def test_preview_changes_do_not_equate_booleans_with_integer_capacities():
    with pytest.raises(PolicySettingsError):
        PolicyChange(BusinessId.STUDY_ROOM, "capacity", True, 1)
    with pytest.raises(PolicySettingsError):
        ResetPreview(YEAR, 1, [], default_weekly_policy())


def test_reset_rejects_a_forged_boolean_that_compares_equal_to_integer_in_preview(repository):
    settings = PolicySettings(repository)
    settings.initialize(YEAR, command_id="init")
    custom = WeeklyPolicy(tuple(
        replace(post, capacity=2) if post.business is BusinessId.STUDY_ROOM else post
        for post in default_weekly_policy().businesses
    ))
    settings.save(YEAR, custom, expected_revision=1, command_id="save")
    preview = settings.preview_reset(YEAR)
    change = next(change for change in preview.changes if change.field == "capacity")
    object.__setattr__(change, "after", True)
    with pytest.raises(PolicySettingsError):
        settings.reset(preview, command_id="reset")
    assert settings.current(YEAR).revision == 2
    assert settings.reset(settings.preview_reset(YEAR), command_id="reset").revision == 3


@pytest.mark.parametrize("invalid", [True, False, 0, -1, 9999, 2026.0, "2026", None])
def test_year_requires_strict_bounded_integer(repository, invalid):
    settings = PolicySettings(repository)
    for operation in (
        lambda: settings.initialize(invalid, command_id="invalid"),
        lambda: settings.current(invalid),
        lambda: settings.revision(invalid, 1),
        lambda: settings.preview_reset(invalid),
        lambda: settings.save(invalid, default_weekly_policy(), expected_revision=1, command_id="invalid"),
    ):
        with pytest.raises(PolicySettingsError):
            operation()
    assert settings.initialize(YEAR, command_id="invalid").revision == 1


@pytest.mark.parametrize("invalid", [True, False, 0, -1, 1.0, "1", None, 2**63, 10**100])
def test_revision_requires_positive_strict_integer(repository, invalid):
    settings = PolicySettings(repository)
    settings.initialize(YEAR, command_id="init")
    with pytest.raises(PolicySettingsError) as read_error:
        settings.revision(YEAR, invalid)
    assert read_error.type is PolicySettingsError
    with pytest.raises(PolicySettingsError) as write_error:
        settings.save(YEAR, custom_policy(), expected_revision=invalid, command_id="save")
    assert write_error.type is PolicySettingsError
    assert settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save").revision == 2


def test_signed_integer_revision_limit_is_readable_but_cannot_be_incremented(repository, request):
    # Reaching this limit naturally would take 2**63 writes. Seed only an
    # isolated storage fixture to exercise the real adapters at the limit.
    maximum = 2**63 - 1
    document = encode_weekly_policy(default_weekly_policy())
    if isinstance(repository, MemoryPolicyRepository):
        stored = StoredPolicyRevision(YEAR, maximum - 1, document)
        repository._revisions[(YEAR, maximum - 1)] = stored
        repository._current[YEAR] = maximum - 1
    else:
        engine, _ = request.getfixturevalue("sqlite_pair")
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO school_year_policy_revisions (year_start, revision, document) VALUES (:year, :revision, :document)"
            ), {"year": YEAR, "revision": maximum - 1, "document": document})
            connection.execute(text(
                "INSERT INTO school_year_policy_current (year_start, revision) VALUES (:year, :revision)"
            ), {"year": YEAR, "revision": maximum - 1})
    settings = PolicySettings(repository)
    last = settings.save(YEAR, custom_policy(), expected_revision=maximum - 1, command_id="last-save")
    assert last.revision == maximum
    assert settings.revision(YEAR, maximum) == last
    assert settings.save(YEAR, custom_policy(), expected_revision=maximum - 1, command_id="last-save") == last
    with pytest.raises(PolicySettingsError, match="capacity"):
        settings.save(YEAR, default_weekly_policy(), expected_revision=maximum, command_id="overflow")
    with pytest.raises(PolicySettingsError, match="capacity"):
        settings.reset(settings.preview_reset(YEAR), command_id="overflow-reset")
    assert settings.current(YEAR) == last


@pytest.mark.parametrize("invalid", [True, False, 1, None, "", " \t", "x" * 65])
def test_commands_require_nonempty_bounded_text(repository, invalid):
    settings = PolicySettings(repository)
    with pytest.raises(PolicySettingsError):
        settings.initialize(YEAR, command_id=invalid)
    assert settings.initialize(YEAR, command_id="x" * 64).revision == 1


def test_commands_require_valid_unicode_but_allow_nonascii_and_nonbmp(repository):
    settings = PolicySettings(repository)
    with pytest.raises(PolicySettingsError):
        settings.initialize(YEAR, command_id="invalid-\ud800")
    with pytest.raises(PolicyNotFound):
        settings.current(YEAR)
    valid_id = "政策修訂-𠮷"
    original = settings.initialize(YEAR, command_id=valid_id)
    assert settings.initialize(YEAR, command_id=valid_id) == original


def test_command_whitespace_is_normalized_before_storage_and_replay(repository):
    settings = PolicySettings(repository)
    original = settings.initialize(YEAR, command_id="  initialize\t")
    assert settings.initialize(YEAR, command_id="initialize") == original
    assert settings.initialize(YEAR, command_id="\ninitialize ") == original
    assert settings.current(YEAR).revision == 1


def test_malformed_nested_typed_input_is_a_settings_error_before_storage(repository):
    settings = PolicySettings(repository)
    original = settings.initialize(YEAR, command_id="init")
    forged = custom_policy()
    object.__setattr__(forged, "businesses", (object(),))
    with pytest.raises(PolicySettingsError):
        settings.save(YEAR, forged, expected_revision=1, command_id="save")
    assert settings.current(YEAR) == original
    assert settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save").revision == 2


def test_invalid_policy_cannot_change_state_or_consume_command(repository):
    settings = PolicySettings(repository)
    original = settings.initialize(YEAR, command_id="init")
    forged = custom_policy()
    object.__setattr__(forged, "businesses", ())
    invalid_unicode = custom_policy()
    object.__setattr__(invalid_unicode.businesses[1], "room", "\ud800")
    for policy in (None, {}, forged, invalid_unicode):
        with pytest.raises(PolicySettingsError):
            settings.save(YEAR, policy, expected_revision=1, command_id="save")
        assert settings.current(YEAR) == original
    assert settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save").revision == 2


def test_missing_year_and_history_are_not_defaulted(repository):
    settings = PolicySettings(repository)
    with pytest.raises(PolicyNotFound):
        settings.revision(YEAR, 1)
    settings.initialize(YEAR, command_id="init")
    with pytest.raises(PolicyNotFound):
        settings.revision(YEAR, 2)
    with pytest.raises(PolicyNotFound):
        settings.preview_reset(YEAR + 1)


def test_corrupt_stored_json_is_storage_error_not_silent_default(repository):
    repository.commit(YEAR, 0, '{"unsupported": true}', "corrupt-test", "0" * 64, operation="initialize")
    settings = PolicySettings(repository)
    with pytest.raises(PolicyStorageError):
        settings.current(YEAR)
    with pytest.raises(PolicyStorageError):
        settings.revision(YEAR, 1)


def test_memory_repositories_are_separate_guest_workspaces():
    left, right = PolicySettings(MemoryPolicyRepository()), PolicySettings(MemoryPolicyRepository())
    left.initialize(YEAR, command_id="init")
    right.initialize(YEAR, command_id="init")
    left.save(YEAR, custom_policy(), expected_revision=1, command_id="save")
    assert right.current(YEAR).policy == default_weekly_policy()
    assert right.current(YEAR).revision == 1
    assert right.save(YEAR, custom_policy("600"), expected_revision=1, command_id="save").policy == custom_policy("600")


def test_concurrent_same_expected_revision_has_one_winner(repository):
    settings = PolicySettings(repository)
    settings.initialize(YEAR, command_id="init")
    start = Barrier(2)

    def save(index):
        start.wait(timeout=5)
        try:
            return PolicySettings(repository).save(YEAR, custom_policy(str(600 + index)), expected_revision=1, command_id=f"save-{index}")
        except PolicyVersionConflict as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(save, (1, 2)))
    assert sum(isinstance(result, PolicyVersionConflict) for result in results) == 1
    assert settings.current(YEAR).revision == 2
    with pytest.raises(PolicyNotFound):
        settings.revision(YEAR, 3)


def test_sqlite_constructor_is_inert_and_schema_initialization_is_explicit(tmp_path):
    database = tmp_path / "not-live.sqlite3"
    engine = create_engine(f"sqlite:///{database}")
    try:
        repository = SQLitePolicyRepository(engine)
        settings = PolicySettings(repository)
        assert not database.exists()
        with pytest.raises(PolicyStorageError):
            settings.current(YEAR)
        assert inspect(engine).get_table_names() == []
        repository.create_schema()
        assert set(inspect(engine).get_table_names()) == {
            "school_year_policy_revisions", "school_year_policy_current", "prelaunch_policy_commands",
        }
        assert settings.initialize(YEAR, command_id="init").revision == 1
    finally:
        engine.dispose()


def test_sqlite_two_independent_engines_serialize_and_restart_replays(sqlite_pair):
    engine, repository = sqlite_pair
    settings = PolicySettings(repository)
    original = settings.initialize(YEAR, command_id="init")
    peer_engine = create_engine(engine.url)
    peer = PolicySettings(SQLitePolicyRepository(peer_engine))
    start = Barrier(2)

    def save(pair):
        service, command = pair
        start.wait(timeout=5)
        try:
            return service.save(YEAR, custom_policy(command), expected_revision=1, command_id=command)
        except PolicyVersionConflict as error:
            return error

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(save, ((settings, "501"), (peer, "502"))))
        assert sum(isinstance(result, PolicyVersionConflict) for result in results) == 1
    finally:
        peer_engine.dispose()
    engine.dispose()
    restarted_engine = create_engine(engine.url)
    try:
        restarted = PolicySettings(SQLitePolicyRepository(restarted_engine))
        assert restarted.current(YEAR).revision == 2
        assert restarted.initialize(YEAR, command_id="init") == original
        winner = next(result for result in results if not isinstance(result, PolicyVersionConflict))
        room = next(post.room for post in winner.policy.businesses if post.business is BusinessId.STUDY_ROOM)
        restarted.save(YEAR, custom_policy("700"), expected_revision=2, command_id="later")
        assert restarted.save(YEAR, custom_policy(room), expected_revision=1, command_id=room) == winner
    finally:
        restarted_engine.dispose()


def test_sqlite_failure_after_all_inserts_rolls_back_revision_pointer_and_receipt(sqlite_pair):
    engine, repository = sqlite_pair
    settings = PolicySettings(repository)
    original = settings.initialize(YEAR, command_id="init")

    def fail_receipt(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO prelaunch_policy_commands"):
            raise OperationalError("simulated command insert", None, RuntimeError("test interruption"))

    event.listen(engine, "after_cursor_execute", fail_receipt)
    try:
        with pytest.raises(PolicyStorageError):
            settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save")
    finally:
        event.remove(engine, "after_cursor_execute", fail_receipt)
    assert settings.current(YEAR) == original
    with engine.connect() as connection:
        for table in ("school_year_policy_revisions", "school_year_policy_current", "prelaunch_policy_commands"):
            assert connection.scalar(text(f"SELECT COUNT(*) FROM {table}")) == 1
    assert settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save").revision == 2


def test_sqlite_releases_read_and_write_connections_before_policy_decoding(sqlite_pair, monkeypatch):
    import roster_core.policy_settings as module

    engine, repository = sqlite_pair
    original_decode = module.decode_weekly_policy
    calls = []

    def decode(document):
        assert engine.pool.checkedout() == 0
        calls.append(document)
        return original_decode(document)

    monkeypatch.setattr(module, "decode_weekly_policy", decode)
    settings = PolicySettings(repository)
    settings.initialize(YEAR, command_id="init")
    settings.current(YEAR)
    settings.revision(YEAR, 1)
    settings.save(YEAR, custom_policy(), expected_revision=1, command_id="save")
    assert len(calls) == 6


def test_sqlite_enforces_declared_foreign_keys_on_fresh_connections(sqlite_pair):
    engine, repository = sqlite_pair
    engine.dispose()
    PolicySettings(repository).initialize(YEAR, command_id="init")
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO school_year_policy_current (year_start, revision) VALUES (2027, 99)"))
