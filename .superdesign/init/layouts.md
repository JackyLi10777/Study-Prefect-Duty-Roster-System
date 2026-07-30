# Layouts — current application shell

Generated from `nicegui_app/ui/shell.py` (1,329 lines). The file is too large to duplicate safely; the complete owning function is `page_shell` at lines 1083–1329 and its responsive helpers are listed below.

## Sole workbench layout

Source outline (python):
    @contextmanager
    def page_shell(active_path: str) -> Iterator[None]:
        page_context = current_page_context()
        adopt_verified_theme_handoff(page_context)
        dark_mode = apply_theme()
        document_language = "en" if current_locale() == "en" else "zh-Hant-HK"
        # resolve PageDefinition, enforce visibility/capability,
        # install Guest snapshot and auth-status monitors,
        # render drawer/header/status/main/mobile navigation/footer,
        # then install theme, focus, drawer and viewport browser runtimes.

The actual function validates the current `PageDefinition`, requires its capability, renders one shared desktop/mobile shell, and yields exactly one `main` content region. Admin and Guest differ through `PageContext`, not layout markup.

## Exact helper ownership

| Function | Lines | Owns |
|---|---:|---|
| `_navigation_context` | 54–67 | chapter/group/icon from canonical page catalog |
| `_install_guest_snapshot_bridge` | 123–272 | per-tab Guest session snapshot lifecycle |
| `_install_auth_status_monitor` | 273–473 | expiry/revocation checks |
| `_render_mobile_drawer_tools` | 734–792 | language, sound, theme, sign-out |
| `_render_mobile_tabbar` | 793–826 | three weekly primary destinations + More |
| `_install_mobile_drawer_accessibility` | 827–992 | focus trap, Escape, inert background |
| `_install_mobile_viewport_accessibility` | 993–1060 | viewport and safe-area behaviour |
| `_install_route_focus_management` | 1061–1082 | heading focus after navigation |
| `page_shell` | 1083–1329 | complete layout assembly |

## Rendered hierarchy

Source outline (text):
    body[data-sy-page][data-sy-page-kind][data-sy-access-mode]
    ├── skip link
    ├── header
    │   ├── drawer trigger + chapter/page title
    │   └── music / mode / language / sound / theme / sign-out controls
    ├── left drawer
    │   ├── Service Weave product mark + functional name
    │   ├── grouped navigation from PAGE_DEFINITIONS
    │   ├── trust/reference destinations
    │   └── feedback links
    ├── access-mode notice when needed
    ├── main#main-content
    │   └── page-owned content
    ├── reference pager when page-owned
    ├── copyright footer
    └── mobile bottom navigation

## Breakpoints and composition

- `> 900px`: persistent drawer and full utility dock.
- `<= 900px`: hidden drawer, compact header, bottom primary navigation, stacked content.
- `320–390px`: one-column reading order, no horizontal overflow, primary actions remain reachable.
- Main content width is governed by semantic layout CSS, not page-specific `max-w-*` classes.

## Layout invariants

1. Current task and safe next action precede story/evidence content on operational pages.
2. Browser Back must remain valid; explicit workflow back/next actions are added only when hierarchy is not inferable.
3. Mobile and desktop use the same data and action ordering.
4. One viewport has at most two simultaneous active motion groups.
5. Page-local background art never sits behind sensitive operational data.
