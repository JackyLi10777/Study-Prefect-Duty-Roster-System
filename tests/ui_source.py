from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT


def combined_page_source() -> str:
    """Return the refactored page contract as one source string for static tests."""

    ui_root = PROJECT_ROOT / "nicegui_app" / "ui"
    files = [ui_root / "page_shared.py", *(sorted((ui_root / "page_routes").glob("*.py")))]
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def combined_theme_source() -> str:
    """Return theme behavior and extracted markup as one static contract."""

    ui_root = PROJECT_ROOT / "nicegui_app" / "ui"
    sources = [
        (ui_root / filename).read_text(encoding="utf-8")
        for filename in ("theme.py", "theme_markup.py")
    ]
    sources.append(
        (PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-theme-v1.css").read_text(encoding="utf-8")
    )
    return "\n".join(sources)


def combined_i18n_source() -> str:
    """Return the message facade and domain catalogues as one static contract."""

    ui_root = PROJECT_ROOT / "nicegui_app" / "ui"
    files = [ui_root / "i18n.py", *(sorted((ui_root / "i18n_catalog").glob("*.py")))]
    return "\n".join(path.read_text(encoding="utf-8") for path in files)
