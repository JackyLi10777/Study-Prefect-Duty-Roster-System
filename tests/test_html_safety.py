from __future__ import annotations

import re
from pathlib import Path

from nicegui_app.ui.html_safety import attr, text


def test_attr_escapes_quotes_and_angle_brackets() -> None:
    assert attr('x" onmouseover=alert(1) x="') == (
        "x&quot; onmouseover=alert(1) x=&quot;"
    )
    assert attr("<script>alert(1)</script>") == (
        "&lt;script&gt;alert(1)&lt;/script&gt;"
    )


def test_text_escapes_markup_while_leaving_plain_quotes() -> None:
    assert text("<b>值班</b>") == "&lt;b&gt;值班&lt;/b&gt;"
    assert text('name "quoted"') == 'name "quoted"'


def test_component_status_and_heading_escape_attribute_and_html_surfaces() -> None:
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "nicegui_app" / "ui" / "components.py").read_text(
        encoding="utf-8"
    )
    assert 'aria-label="{attr(text)}"' in source
    assert "ui.html(text(title), tag=" in source
    assert "from nicegui_app.ui.html_safety import attr, text" in source


def test_mobile_cards_escape_user_visible_aria_labels() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "nicegui_app" / "ui" / "page_shared.py"
    ).read_text(encoding="utf-8")
    assert 'aria-label="{attr(card_label)}"' in source
    assert 'attr(day_rows[0]["day"])' in source


def test_all_interpolated_ui_aria_labels_use_attribute_escaping() -> None:
    """Keep future translated or record-derived labels inside one safe attribute boundary."""

    ui_root = Path(__file__).resolve().parents[1] / "nicegui_app" / "ui"
    unsafe: list[str] = []
    pattern = re.compile(r'aria-label="\{(?!attr\()')
    for source_path in sorted(ui_root.rglob("*.py")):
        for line_number, line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                unsafe.append(f"{source_path.relative_to(ui_root)}:{line_number}")
    assert unsafe == []
