from __future__ import annotations

from fastapi import APIRouter

from roster_core.generator import generate_weekly_roster
from roster_core.loaders import load_prefect_seed


router = APIRouter()


@router.get("/preview")
def preview_roster() -> dict:
    prefects = load_prefect_seed()
    assignments = generate_weekly_roster(prefects)
    return {
        "source": "data/demo/prefects.zh-HK.seed.json",
        "assignments": [assignment.to_dict() for assignment in assignments],
    }

