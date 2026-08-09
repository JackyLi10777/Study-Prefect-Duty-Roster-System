from __future__ import annotations

from dataclasses import dataclass

import pytest

from nicegui_app.services.roster_workflow import PrefectPatch
from nicegui_app.ui.edit_sessions import PrefectEditSession
from nicegui_app.ui.page_routes.people import (
    _apply_prefect_patch_batch,
    _prefect_directory_view,
)


def _row(
    prefect_id: str,
    name: str,
    *,
    form: str,
    class_name: str,
    role: str = "study_prefect",
    weight: float = 0,
    duties: int = 0,
    mentoring: bool = False,
    created: str = "2026-07-01T00:00:00",
) -> dict[str, object]:
    return {
        "id": prefect_id,
        "nameZh": name,
        "nameEn": f"{name} English",
        "form": form,
        "className": class_name,
        "roleCode": role,
        "historyWeight": weight,
        "historyDuties": duties,
        "needsMentoring": mentoring,
        "availableDays": ["MONDAY", "WEDNESDAY"],
        "fixedGeneralDuty": "NONE",
        "remarks": "",
        "version": 1,
        "createdAt": created,
    }


def test_directory_search_filter_and_sort_share_one_stable_model() -> None:
    rows = [
        _row("p2", "陳安", form="F.5", class_name="5A", weight=4, duties=3),
        _row(
            "p1",
            "李明",
            form="F.3",
            class_name="3B",
            role="assistant_head",
            mentoring=True,
            created="2026-06-01T00:00:00",
        ),
        _row("p3", "張心", form="F.4", class_name="4C", weight=2, duties=1),
    ]

    assert [item["id"] for item in _prefect_directory_view(rows, query="明")] == ["p1"]
    assert [item["id"] for item in _prefect_directory_view(rows, query="4C")] == ["p3"]
    assert [item["id"] for item in _prefect_directory_view(rows, form_filter="F.5")] == ["p2"]
    assert [item["id"] for item in _prefect_directory_view(rows, support_filter="needs_mentoring")] == ["p1"]
    assert [item["id"] for item in _prefect_directory_view(rows, sort_code="grade_asc")] == ["p1", "p3", "p2"]
    assert [item["id"] for item in _prefect_directory_view(rows, sort_code="weight_desc")] == ["p2", "p3", "p1"]


@dataclass
class _Workflow:
    conflict_id: str | None = None
    invalid_id: str | None = None
    writes: list[str] | None = None

    def patch_prefects_batch(
        self,
        patches: tuple[PrefectPatch, ...],
        *,
        command_id: str,
    ) -> dict[str, object]:
        assert command_id == "batch-command"
        invalid = next((patch for patch in patches if patch.prefect_id == self.invalid_id), None)
        if invalid is not None:
            return {
                "updated": [],
                "conflicts": [],
                "errors": [{"prefectId": invalid.prefect_id, "message": "invalid row"}],
            }
        conflict = next((patch for patch in patches if patch.prefect_id == self.conflict_id), None)
        if conflict is not None:
            return {
                "updated": [],
                "conflicts": [
                    {
                        "prefectId": conflict.prefect_id,
                        "latest": {"id": conflict.prefect_id, "version": 9, "className": "5Z"},
                        "changes": dict(conflict.changes),
                    }
                ],
                "errors": [],
            }
        if self.writes is not None:
            self.writes.extend(patch.prefect_id for patch in patches)
        return {
            "updated": [
                {
                    "id": patch.prefect_id,
                    "version": patch.expected_version + 1,
                    **patch.changes,
                }
                for patch in patches
            ],
            "conflicts": [],
            "errors": [],
        }


def test_batch_patch_preserves_conflicting_input_and_latest_record() -> None:
    writes: list[str] = []
    result = _apply_prefect_patch_batch(
        _Workflow(conflict_id="p2", writes=writes),
        (
            PrefectPatch("p1", {"className": "5A"}, 2),
            PrefectPatch("p2", {"remarks": "本頁輸入"}, 3),
        ),
        command_id="batch-command",
    )

    assert result["updated"] == []
    assert result["conflicts"] == [
        {
            "prefectId": "p2",
            "latest": {"id": "p2", "version": 9, "className": "5Z"},
            "changes": {"remarks": "本頁輸入"},
        }
    ]
    assert result["errors"] == []
    assert writes == []


def test_batch_patch_validates_every_row_before_the_first_write() -> None:
    writes: list[str] = []
    workflow = _Workflow(invalid_id="p2", writes=writes)

    result = _apply_prefect_patch_batch(
        workflow,
        (
            PrefectPatch("p1", {"className": "5A"}, 2),
            PrefectPatch("p2", {"form": "F.7"}, 3),
        ),
        command_id="batch-command",
    )

    assert result == {
        "updated": [],
        "conflicts": [],
        "errors": [{"prefectId": "p2", "message": "invalid row"}],
    }
    assert writes == []


def test_typed_prefect_session_owns_staging_retry_and_conflict_reapplication() -> None:
    commands = iter(("batch-1", "batch-2", "batch-3"))
    session = PrefectEditSession.from_rows(
        [
            _row("p1", "李明", form="F.3", class_name="3A"),
            _row("p2", "陳安", form="F.4", class_name="4B"),
        ],
        command_factory=lambda: next(commands),
    )

    assert session.stage("p1", "remarks", "本頁輸入") is True
    assert session.command_id == "batch-1"
    assert session.ensure_command_id() == "batch-1"
    assert session.stage("p2", "className", "4Z") is True
    assert session.command_id == "batch-2"
    session.update_filter("query", "4Z")
    assert [row["id"] for row in session.visible_rows()] == ["p2"]
    session.update_filter("query", "")
    assert [patch.prefect_id for patch in session.patches()] == ["p1", "p2"]

    session.apply_save_result(
        {
            "updated": [],
            "conflicts": [
                {
                    "prefectId": "p2",
                    "latest": {**session.originals["p2"], "version": 7},
                    "changes": {"className": "4Z"},
                }
            ],
            "errors": [],
        }
    )
    assert session.pending["p1"] == {"remarks": "本頁輸入"}
    assert session.pending["p2"] == {"className": "4Z"}
    assert session.reapply_conflict("p2") is True
    assert session.originals["p2"]["version"] == 7
    assert session.pending["p2"] == {"className": "4Z"}
    assert session.command_id == "batch-3"

    with pytest.raises(ValueError, match="partial"):
        session.apply_save_result(
            {
                "updated": [{**session.originals["p1"], "version": 2}],
                "conflicts": [{"prefectId": "p2", "latest": session.originals["p2"]}],
                "errors": [],
            }
        )


def test_directory_source_uses_immutable_id_and_responsive_shared_editor() -> None:
    source = (
        __import__("pathlib").Path(__file__).parents[1]
        / "nicegui_app"
        / "ui"
        / "page_routes"
        / "people.py"
    ).read_text(encoding="utf-8")
    assert 'data-prefect-id="{attr(prefect_id)}"' in source
    assert "_render_inline_prefect_directory(" in source
    assert "edit_session = PrefectEditSession.from_rows(prefects)" in source
    assert "sy-prefect-directory-desktop" not in source
    assert "discard_conflicted_row" in source
    assert "reapply_conflicted_row" in source
    assert "prefect_inline_use_latest" in source
    assert "prefect_inline_reapply" in source
    assert 'wait_kind="ai"' in source
