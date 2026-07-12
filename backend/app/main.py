from __future__ import annotations

from fastapi import FastAPI

from app.api.devotional import router as devotional_router
from app.api.roster import router as roster_router


app = FastAPI(
    title="Sing Yin Study Prefect Duty Roster System",
    version="0.1.0",
    description="Local-first FastAPI backend for the code_v3 rebuild.",
)

app.include_router(devotional_router, prefix="/api/devotional", tags=["devotional"])
app.include_router(roster_router, prefix="/api/roster", tags=["roster"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sing-yin-duty-roster"}

