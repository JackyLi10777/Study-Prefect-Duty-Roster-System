from __future__ import annotations

from dataclasses import dataclass

import pytest

from nicegui_app.services.roster_workflow import WorkflowConflictError, WorkflowError
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

    def validate_prefect_patch(
        self,
        prefect_id: str,
        changes: dict[str, object],
        *,
        expected_version: int,
    ) -> None:
        del changes, expected_version
        if prefect_id == self.invalid_id:
            raise WorkflowError("invalid row")

    def patch_prefect(
        self,
        prefect_id: str,
        changes: dict[str, object],
        *,
        expected_version: int,
        command_id: str,
    ) -> dict[str, object]:
        assert command_id
        if self.writes is not None:
            self.writes.append(prefect_id)
        if prefect_id == self.conflict_id:
            raise WorkflowConflictError("stale")
        return {"id": prefect_id, "version": expected_version + 1, **changes}

    def prefect(self, prefect_id: str) -> dict[str, object]:
        return {"id": prefect_id, "version": 9, "className": "5Z"}


def test_batch_patch_preserves_conflicting_input_and_latest_record() -> None:
    result = _apply_prefect_patch_batch(
        _Workflow(conflict_id="p2"),
        (
            {
                "prefectId": "p1",
                "changes": {"className": "5A"},
                "expectedVersion": 2,
                "commandId": "cmd-1",
            },
            {
                "prefectId": "p2",
                "changes": {"remarks": "本頁輸入"},
                "expectedVersion": 3,
                "commandId": "cmd-2",
            },
        ),
    )

    assert result["updated"] == [{"id": "p1", "version": 3, "className": "5A"}]
    assert result["conflicts"] == [
        {
            "prefectId": "p2",
            "latest": {"id": "p2", "version": 9, "className": "5Z"},
            "changes": {"remarks": "本頁輸入"},
        }
    ]
    assert result["errors"] == []


def test_batch_patch_validates_every_row_before_the_first_write() -> None:
    writes: list[str] = []
    workflow = _Workflow(invalid_id="p2", writes=writes)

    result = _apply_prefect_patch_batch(
        workflow,
        (
            {
                "prefectId": "p1",
                "changes": {"className": "5A"},
                "expectedVersion": 2,
                "commandId": "cmd-1",
            },
            {
                "prefectId": "p2",
                "changes": {"form": "F.7"},
                "expectedVersion": 3,
                "commandId": "cmd-2",
            },
        ),
    )

    assert result == {
        "updated": [],
        "conflicts": [],
        "errors": [{"prefectId": "p2", "message": "invalid row"}],
    }
    assert writes == []


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
    assert "sy-prefect-directory-desktop" not in source
    assert "discard_conflicted_row" in source
    assert "reapply_conflicted_row" in source
    assert "prefect_inline_use_latest" in source
    assert "prefect_inline_reapply" in source
    assert 'wait_kind="ai"' in source
