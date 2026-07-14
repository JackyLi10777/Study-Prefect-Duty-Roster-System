from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from nicegui_app.services.roster_workflow import PrefectInput, RosterWorkflow, WorkflowConflictError, WorkflowError
from nicegui_app.utils.prefect_import import parse_prefect_import_text, prefect_import_template_csv


def _workflow(tmp_path) -> RosterWorkflow:
    workflow = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    workflow.bootstrap()
    return workflow


def test_prefect_can_be_created_updated_and_archived_without_erasing_history(tmp_path) -> None:
    workflow = _workflow(tmp_path)
    created = workflow.create_prefect(
        PrefectInput(
            name_zh="許朗然",
            form="F.4",
            class_name="4H",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY", "FRIDAY"),
            needs_mentoring=False,
            remarks="Test record",
        )
    )

    updated = workflow.update_prefect(
        created["id"],
        PrefectInput(
            name_zh="許朗然",
            form="F.4",
            class_name="4H",
            role_code="study_prefect",
            available_days=("TUESDAY", "THURSDAY"),
            needs_mentoring=True,
            remarks="Updated availability",
        ),
    )
    workflow.archive_prefect(created["id"])

    assert updated["availableDays"] == ["TUESDAY", "THURSDAY"]
    assert updated["needsMentoring"] is True
    assert created["id"] not in {item["id"] for item in workflow.prefects()}
    assert len(list((tmp_path / "backups").glob("*.sqlite3"))) == 3


def test_stale_prefect_editor_cannot_overwrite_a_newer_saved_version(tmp_path) -> None:
    workflow = _workflow(tmp_path)
    original = workflow.prefect(str(workflow.prefects()[0]["id"]))
    first_edit = PrefectInput(
        name_zh=str(original["nameZh"]),
        name_en=original["nameEn"],
        form=str(original["form"]),
        class_name=str(original["className"]),
        role_code=str(original["roleCode"]),
        available_days=tuple(original["availableDays"]),
        needs_mentoring=bool(original["needsMentoring"]),
        remarks="First browser saved this note",
    )
    stale_edit = PrefectInput(
        **{**first_edit.__dict__, "remarks": "Stale browser tried to overwrite it"}
    )

    saved = workflow.update_prefect(
        str(original["id"]),
        first_edit,
        expected_version=int(original["version"]),
    )

    with pytest.raises(WorkflowConflictError, match="another browser"):
        workflow.update_prefect(
            str(original["id"]),
            stale_edit,
            expected_version=int(original["version"]),
        )

    current = workflow.prefect(str(original["id"]))
    assert saved["version"] == int(original["version"]) + 1
    assert current["remarks"] == "First browser saved this note"


def test_stale_prefect_archive_cannot_hide_a_newer_saved_version(tmp_path) -> None:
    workflow = _workflow(tmp_path)
    original = workflow.prefect(str(workflow.prefects()[0]["id"]))
    edited = workflow.update_prefect(
        str(original["id"]),
        PrefectInput(
            name_zh=str(original["nameZh"]),
            name_en=original["nameEn"],
            form=str(original["form"]),
            class_name=str(original["className"]),
            role_code=str(original["roleCode"]),
            available_days=tuple(original["availableDays"]),
            needs_mentoring=bool(original["needsMentoring"]),
            remarks="Latest reviewed record",
        ),
        expected_version=int(original["version"]),
    )

    with pytest.raises(WorkflowConflictError, match="another browser"):
        workflow.archive_prefect(
            str(original["id"]),
            expected_version=int(original["version"]),
        )

    current = workflow.prefect(str(original["id"]))
    assert current["active"] is True
    assert current["version"] == edited["version"]
    workflow.archive_prefect(str(original["id"]), expected_version=int(edited["version"]))
    assert workflow.prefect(str(original["id"]))["active"] is False


def test_concurrent_duplicate_chinese_name_creation_has_one_winner(tmp_path) -> None:
    database_path = tmp_path / "sing-yin.sqlite3"
    backup_dir = tmp_path / "backups"
    first = RosterWorkflow(database_path=database_path, backup_dir=backup_dir)
    second = RosterWorkflow(database_path=database_path, backup_dir=backup_dir)
    first.bootstrap()
    second.bootstrap()
    barrier = Barrier(2)
    prefect_input = PrefectInput(
        name_zh="測試風紀甲",
        form="F.4",
        class_name="4H",
        role_code="study_prefect",
        available_days=("MONDAY", "WEDNESDAY"),
    )

    def create(service: RosterWorkflow):
        barrier.wait(timeout=5)
        try:
            return service.create_prefect(prefect_input)
        except WorkflowError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(create, (first, second)))

    assert len([item for item in outcomes if isinstance(item, dict)]) == 1
    errors = [item for item in outcomes if isinstance(item, WorkflowError)]
    assert len(errors) == 1
    assert "Chinese name already exists" in str(errors[0])
    assert [item["nameZh"] for item in first.prefects()].count("測試風紀甲") == 1


def test_ai_import_preview_normalizes_traditional_chinese_csv_before_persistence(tmp_path) -> None:
    preview = parse_prefect_import_text(
        "姓名,級別,班別,職務,可值班日\n"
        "梁子軒,F.3,3H,導學風紀,星期一、星期三、星期五\n"
        "范皓朗,F.5,5F,助理首席導學風紀,星期二、星期四\n"
    )
    workflow = _workflow(tmp_path)
    imported = workflow.import_prefects(preview.rows)

    assert preview.issues == ()
    assert {item["nameZh"] for item in imported} == {"梁子軒", "范皓朗"}
    assert {item["roleCode"] for item in imported} == {"study_prefect", "assistant_head"}


def test_downloadable_import_template_contains_only_fictional_rows_that_pass_preview_validation() -> None:
    template = prefect_import_template_csv().decode("utf-8-sig")
    preview = parse_prefect_import_text(template)

    assert "姓名,級別,班別,職務,可值班日,備註" in template
    assert preview.issues == ()
    assert [row.name_zh for row in preview.rows] == ["範例風紀甲", "範例風紀乙"]


def test_english_only_name_is_rejected_by_preview_and_workflow_boundary(tmp_path) -> None:
    preview = parse_prefect_import_text(
        "姓名,級別,班別,職務,可值班日\nTest Prefect,F.3,3H,導學風紀,星期一\n"
    )
    assert preview.rows == ()
    assert "display name must be Chinese" in preview.issues[0]

    workflow = _workflow(tmp_path)
    with pytest.raises(WorkflowError, match="display name must be Chinese"):
        workflow.create_prefect(
            PrefectInput(
                name_zh="Test Prefect",
                form="F.3",
                class_name="3H",
                role_code="study_prefect",
                available_days=("MONDAY",),
            )
        )
