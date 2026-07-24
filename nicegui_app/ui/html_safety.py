"""Small HTML escaping helpers for attribute and markup interpolation."""

from __future__ import annotations

import html


def attr(value: object) -> str:
    """Escape a value for safe inclusion inside a double-quoted HTML attribute."""

    return html.escape(str(value), quote=True)


def text(value: object) -> str:
    """Escape a value for safe inclusion as HTML text content."""

    return html.escape(str(value), quote=False)


__all__ = ["attr", "text"]
