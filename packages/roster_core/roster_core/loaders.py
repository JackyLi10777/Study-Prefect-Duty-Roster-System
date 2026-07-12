from __future__ import annotations

import json
from pathlib import Path

from .models import Prefect


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PREFECTS_PATH = PROJECT_ROOT / "data" / "demo" / "prefects.zh-HK.seed.json"


def load_prefect_seed(path: Path = DEFAULT_PREFECTS_PATH) -> list[Prefect]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Prefect.from_seed(raw) for raw in data["prefects"]]

