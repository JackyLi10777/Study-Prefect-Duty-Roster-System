from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from nicegui_app.config import DISPLAY_PRINT_CREST_PATH, PREFECT_SEED_PATH
from nicegui_app.persistence.models import RosterAssignmentRecord
from nicegui_app.services.roster_export import (
    GRID,
    _register_cjk_fonts,
    _schedule_grid,
    _school_badge,
    _styles,
    build_fairness_audit_pdf,
    build_roster_pdf,
)
from nicegui_app.services.roster_workflow import RosterWorkflow
from nicegui_app.services.workflow_types import DraftDayEdit, DraftSlotStateEdit


def _embedded_font_names(reader: PdfReader) -> set[str]:
    names: set[str] = set()
    for page in reader.pages:
        resources = page.get("/Resources", {})
        fonts = resources.get("/Font", {})
        for font in fonts.values():
            descriptor = font.get_object()
            names.add(str(descriptor.get("/BaseFont", "")))
    return names


def test_pdf_badge_uses_the_full_resolution_display_print_crest() -> None:
    badge = _school_badge()

    assert badge is not None
    assert Path(badge.filename).resolve() == DISPLAY_PRINT_CREST_PATH.resolve()


def test_schedule_pdf_uses_single_page_weekly_grid_and_keeps_chinese_names(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))

    export = build_roster_pdf(workflow, draft.id, language="en")
    reader = PdfReader(BytesIO(export.content))

    assert export.filename == "SYSS_Roster_20260907_v1_EN.pdf"
    assert export.content.startswith(b"%PDF")
    assert len(reader.pages) == 1
    assert float(reader.pages[0].mediabox.width) > float(reader.pages[0].mediabox.height)
    extracted_text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Sing Yin Secondary School Study Prefect Duty Roster" in extracted_text
    assert "MONDAY" in extracted_text
    assert "07 SEP" in extracted_text
    assert "11 SEP" in extracted_text
    assert "Homework Completion Room - 1" in extracted_text
    assert "15:40–18:30" not in extracted_text
    assert "15:40–17:00" in extracted_text
    assert workflow.assignments(draft.id)[0]["prefectName"] in extracted_text
    font_names = _embedded_font_names(reader)
    assert not any("Thin" in name for name in font_names)
    assert any("Medium" in name for name in font_names)
    assert any("SemiBold" in name for name in font_names)
    assert "Not to be served" not in extracted_text
    assert "Internal school document" not in extracted_text
    assert [item["day"] for item in workflow.assignments(draft.id)] == sorted(
        (item["day"] for item in workflow.assignments(draft.id)),
        key=lambda day: ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY").index(day),
    )


def test_schedule_pdf_uses_the_workflow_atomic_schedule_snapshot(tmp_path, monkeypatch) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "snapshot.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    snapshot_week, snapshot_assignments = workflow.roster_schedule_snapshot(draft.id)

    monkeypatch.setattr(
        workflow,
        "roster_schedule_snapshot",
        lambda _roster_week_id: (snapshot_week, snapshot_assignments),
    )
    monkeypatch.setattr(
        workflow,
        "roster_week",
        lambda _roster_week_id: (_ for _ in ()).throw(AssertionError("separate week read")),
    )
    monkeypatch.setattr(
        workflow,
        "assignments",
        lambda _roster_week_id: (_ for _ in ()).throw(AssertionError("separate assignment read")),
    )

    export = build_roster_pdf(workflow, draft.id, language="zh")

    assert export.filename.endswith(f"_v{snapshot_week['version']}_中文.pdf")
    assert export.content.startswith(b"%PDF")
    assert export.roster_status == snapshot_week["status"]
    assert export.roster_version == snapshot_week["version"]


def test_schedule_pdf_renders_a_whole_day_closure_as_one_distinct_column(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "closed-day.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        day_edits=(DraftDayEdit(day="WEDNESDAY", closed=True),),
        command_id="close-wednesday-for-pdf",
    )
    week, assignments = workflow.roster_schedule_snapshot(draft.id)
    table = _schedule_grid(
        assignments,
        week,
        "zh",
        _styles(_register_cjk_fonts()),
        landscape_mode=True,
    )
    wednesday_column = 3

    assert ("SPAN", (wednesday_column, 1), (wednesday_column, -1)) in table._spanCmds
    assert any(
        command[:5]
        == ("BOX", (wednesday_column, 1), (wednesday_column, -1), 0.38, GRID)
        for command in table._linecmds
    )
    extracted_text = "\n".join(
        page.extract_text()
        for page in PdfReader(
            BytesIO(build_roster_pdf(workflow, draft.id, language="zh").content)
        ).pages
    )
    assert extracted_text.count("全天不開放") == 1


def test_chinese_schedule_pdf_distinguishes_week_local_unavailable_from_room_closed(
    tmp_path: Path,
) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        slot_edits=(
            DraftSlotStateEdit(
                cell_key="MONDAY:ROOM_302:1",
                state="unavailable",
            ),
        ),
        command_id="close-one-slot-for-pdf",
    )

    chinese_text = "\n".join(
        page.extract_text()
        for page in PdfReader(
            BytesIO(build_roster_pdf(workflow, draft.id, language="zh").content)
        ).pages
    )

    assert chinese_text.count("本週不開放") == 1
    assert chinese_text.count("不開放") == 5


def test_group_schedule_crest_and_footer_are_explicit_export_options(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))

    clean = PdfReader(BytesIO(build_roster_pdf(workflow, draft.id, language="en", show_crest=False).content))
    annotated = PdfReader(
        BytesIO(
            build_roster_pdf(
                workflow,
                draft.id,
                language="en",
                show_crest=True,
                show_footer_note=True,
            ).content
        )
    )
    clean_text = "\n".join(page.extract_text() for page in clean.pages)
    annotated_text = "\n".join(page.extract_text() for page in annotated.pages)

    assert not clean.pages[0].get("/Resources", {}).get("/XObject")
    assert annotated.pages[0].get("/Resources", {}).get("/XObject")
    assert "Not to be served" not in clean_text
    assert "Internal school document" not in clean_text
    assert "Not to be served" in annotated_text
    assert "Internal school document" in annotated_text


def test_bilingual_published_schedule_pdfs_expose_every_operator_check(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    workflow.publish(draft.id, expected_week_version=draft.version)
    authoritative_names = {str(item["prefectName"]) for item in workflow.assignments(draft.id)}

    chinese_text = "\n".join(
        page.extract_text() for page in PdfReader(BytesIO(build_roster_pdf(workflow, draft.id, language="zh").content)).pages
    )
    english_text = "\n".join(
        page.extract_text() for page in PdfReader(BytesIO(build_roster_pdf(workflow, draft.id, language="en").content)).pages
    )

    for name in authoritative_names:
        assert name in chinese_text
        assert name in english_text
    for label in ("星期一", "星期二", "星期三", "星期四", "星期五", "已發布"):
        assert label in chinese_text
    for label in ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "Published"):
        assert label in english_text
    for label in (
        "Assist. in charge",
        "Room 302 Study Room",
        "Homework Completion Room - 1",
        "Homework Completion Room - 2",
        "Room 202 F1 Study Group - 1",
        "Room 202 F1 Study Group - 2",
    ):
        assert label in chinese_text
        assert label in english_text
    for date_label in ("07 SEP", "08 SEP", "09 SEP", "10 SEP", "11 SEP"):
        assert date_label in english_text
    for date_label in ("9月7日", "9月8日", "9月9日", "9月10日", "9月11日"):
        assert date_label in chinese_text
    assert chinese_text.count("15:40–18:30") == 0
    assert chinese_text.count("15:40–17:00") == 6
    assert english_text.count("15:40–18:30") == 0
    assert english_text.count("15:40–17:00") == 6
    # Two Room 202 rows are closed on both Tuesday and Friday.
    assert chinese_text.count("不開放") == 4
    assert english_text.count("Closed") == 4


def test_chinese_schedule_pdf_keeps_duty_post_names_in_authoritative_english(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))

    export = build_roster_pdf(workflow, draft.id, language="zh")
    extracted_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(export.content)).pages)

    assert "Assist. in charge" in extracted_text
    assert "助理首席導學風紀當值" not in extracted_text


def test_pdf_export_escapes_a_prefect_name_without_breaking_the_document(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    with workflow._session() as session:  # exercise imported names with PDF-sensitive characters
        assignment_id = int(workflow.assignments(draft.id)[0]["id"])
        assignment = session.get(RosterAssignmentRecord, assignment_id)
        assert assignment is not None
        assignment.prefect_name_snapshot = "測試 & <風紀>"
        session.commit()

    export = build_roster_pdf(workflow, draft.id)

    assert export.content.startswith(b"%PDF")


def test_internal_audit_pdf_is_separate_from_group_schedule(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))

    export = build_fairness_audit_pdf(workflow, draft.id, language="en")
    reader = PdfReader(BytesIO(export.content))
    extracted_text = "\n".join(page.extract_text() for page in reader.pages)

    assert export.filename == "SYSS_Fairness_Audit_20260907_EN.pdf"
    assert float(reader.pages[0].mediabox.height) > float(reader.pages[0].mediabox.width)
    assert "Persistent workload ledger" in extracted_text
    assert "Internal record:" in extracted_text
    assert workflow.fairness_rows()[0]["nameZh"] in extracted_text


def test_corrected_published_pdfs_show_the_substitute_and_reconciled_transfer(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    workflow.publish(draft.id, expected_week_version=draft.version)
    assignment = next(item for item in workflow.assignments(draft.id) if item["postCode"] == "ROOM_302")
    replacement = workflow.recommend_substitutes(draft.id, int(assignment["id"]))[0]
    before_loads = workflow.prefect_loads()
    before_text = {
        language: "\n".join(
            page.extract_text()
            for page in PdfReader(BytesIO(build_roster_pdf(workflow, draft.id, language=language).content)).pages
        )
        for language in ("zh", "en")
    }

    outcome = workflow.apply_leave_adjustment(
        roster_week_id=draft.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=str(replacement["id"]),
        reason="已確認的校內活動",
        command_id="pdf-correction-transfer",
        expected_week_version=int(workflow.roster_week(draft.id)["version"]),
    )
    after_loads = workflow.prefect_loads()

    for language in ("zh", "en"):
        corrected_text = "\n".join(
            page.extract_text()
            for page in PdfReader(BytesIO(build_roster_pdf(workflow, draft.id, language=language).content)).pages
        )
        assert corrected_text.count(str(assignment["prefectName"])) == before_text[language].count(
            str(assignment["prefectName"])
        ) - 1
        assert corrected_text.count(str(replacement["nameZh"])) == before_text[language].count(
            str(replacement["nameZh"])
        ) + 1

    assert outcome.status == "replaced"
    assert build_roster_pdf(workflow, draft.id, language="zh").filename == "SYSS_Roster_20260907_v2_中文.pdf"
    assert after_loads[str(assignment["prefectId"])] == before_loads[str(assignment["prefectId"])] - float(
        assignment["weight"]
    )
    assert after_loads[str(replacement["id"])] == before_loads[str(replacement["id"])] + float(
        assignment["weight"]
    )
    assert workflow.reconcile_fairness().balanced


def test_practice_pdfs_are_unmistakably_non_official_in_both_languages(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "practice.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))

    chinese = build_roster_pdf(workflow, draft.id, language="zh", practice=True)
    english = build_fairness_audit_pdf(workflow, draft.id, language="en", practice=True)
    chinese_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(chinese.content)).pages)
    english_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(english.content)).pages)

    assert chinese.filename.startswith("PRACTICE_")
    assert english.filename.startswith("PRACTICE_")
    assert "練習版本" in chinese_text and "不可作正式發布" in chinese_text
    assert "PRACTICE VERSION" in english_text and "NOT FOR OFFICIAL DISTRIBUTION" in english_text


def test_handover_readiness_reports_real_local_state(tmp_path) -> None:
    workflow = RosterWorkflow(
        database_path=tmp_path / "live.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))

    readiness = workflow.handover_readiness()

    assert readiness["activePrefectCount"] > 0
    assert readiness["rosterCount"] == 1
    assert readiness["verifiedBackup"] is True
    assert readiness["backupPath"] == draft.backup_path
