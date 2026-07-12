from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from roster_core import get_foundational_verse, select_daily_verse


router = APIRouter()


@router.get("/daily")
def daily_verse(
    target_date: date | None = Query(default=None),
    special_use: str | None = Query(default=None),
) -> dict:
    return select_daily_verse(target_date, special_use=special_use).to_dict()


@router.get("/foundational")
def foundational_verse() -> dict:
    return get_foundational_verse().to_dict()

