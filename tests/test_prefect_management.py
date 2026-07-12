from __future__ import annotations

from nicegui_app.services.roster_workflow import PrefectInput, RosterWorkflow
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
