from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INIT_ROOT = PROJECT_ROOT / ".superdesign" / "init"
EXPECTED_FILES = {
    "components.md",
    "layouts.md",
    "routes.md",
    "theme.md",
    "pages.md",
    "extractable-components.md",
}

FORBIDDEN_PATH_FRAGMENTS = (
    "data/runtime",
    "data/backups",
    "data/practice",
    "logs/",
    "output/",
    "local-imports/",
)
FORBIDDEN_FILE_SUFFIXES = (
    ".sqlite",
    ".sqlite3",
    ".db",
    ".pdf",
    ".zip",
    ".csv",
    ".xls",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
)
FORBIDDEN_SECRET_MARKERS = (
    "begin private key",
    "admin_bearer_token=",
    "admin_session_secret=",
    "sing_yin_storage_secret=",
)


def test_superdesign_init_is_complete_concise_and_safe() -> None:
    assert INIT_ROOT.is_dir()
    assert EXPECTED_FILES <= {path.name for path in INIT_ROOT.iterdir() if path.is_file()}

    for filename in EXPECTED_FILES:
        path = INIT_ROOT / filename
        text = path.read_text(encoding="utf-8")
        normalized = text.replace("\\", "/").lower()

        assert text.startswith("# ")
        assert "nicegui_app/" in normalized or "design_system/" in normalized
        assert path.stat().st_size < 30_000
        assert "```" not in text
        assert not re.search(r"(?i)(?:[a-z]:\\|\\\\\?\\)", text)
        assert not re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", text, flags=re.IGNORECASE)
        assert not any(fragment in normalized for fragment in FORBIDDEN_PATH_FRAGMENTS)
        assert not any(suffix in normalized for suffix in FORBIDDEN_FILE_SUFFIXES)
        assert not any(marker in normalized for marker in FORBIDDEN_SECRET_MARKERS)

    gitignore_lines = {
        line.strip() for line in (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    assert ".superdesign/tmp/" in gitignore_lines
