"""Versioned head links for the executable Service Weave design system.

The order is an API: foundations load before semantic components, page
narrative and interaction feedback.  The three compatibility layers preserve
the mature rc9 surface language while selectors are migrated into the public
component system; they are named explicitly so they cannot become invisible
global overrides.
"""


STYLE_LAYERS = (
    ("tokens", "/assets/css/sing-yin-tokens-v1.css", None),
    ("base", "/assets/css/sing-yin-base-v1.css", None),
    ("layout", "/assets/css/sing-yin-layout-v1.css", None),
    ("compatibility-theme", "/assets/css/sing-yin-theme-v1.css", None),
    ("compatibility-material", "/assets/css/sing-yin-material-v1.css", None),
    ("components", "/assets/css/sing-yin-components-v1.css", None),
    ("narrative", "/assets/css/sing-yin-narrative-v1.css", None),
    ("compatibility-interaction", "/assets/css/sing-yin-interaction-v1.css", None),
    ("motion", "/assets/css/sing-yin-motion-v1.css", None),
    ("mobile", "/assets/css/sing-yin-mobile-v1.css", "(max-width: 900px)"),
)


def _style_links() -> str:
    links: list[str] = []
    for layer, href, media in STYLE_LAYERS:
        media_attribute = f' media="{media}"' if media else ""
        links.append(
            f'<link rel="stylesheet" href="{href}" '
            f'data-sy-style-layer="{layer}"{media_attribute}>'
        )
    return "\n".join(links)


THEME_HEAD_HTML = (
    '<link rel="preload" href="/assets/fonts/InterVariable.woff2" '
    'as="font" type="font/woff2" crossorigin>\n'
    + _style_links()
    + '\n<script defer src="/assets/runtime/music/sing-yin-music-controller.js" '
    'data-sy-runtime="music-controller"></script>\n'
)


__all__ = ("STYLE_LAYERS", "THEME_HEAD_HTML")
