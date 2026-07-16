# Shared Layouts

## Canonical app shell

Source: [`nicegui_app/ui/shell.py`](../../nicegui_app/ui/shell.py)

`page_shell(title_key, active_path, music_context=None)` is the sole shared layout wrapper. Every primary page uses it.

### Rendered structure

1. Apply the current light or dark theme and Quasar palette.
2. Set the document language and install the dirty-form navigation guard.
3. Resolve access mode, navigation chapter, page slug, and current icon.
4. Render the responsive navigation drawer.
5. Render the application header and utility dock.
6. Render practice, Guest, or maintenance status when active.
7. Render `<main>` with stable page, domain, and mode attributes.
8. Render the mobile bottom navigation after main content in DOM order.
9. Install mobile drawer focus, Escape-key, and focus-trap behaviour.

## Desktop shell

### Sidebar

- School identity and service principle.
- Four navigation groups:
  - Weekly work: Dashboard and Rosters.
  - People and fairness: Prefects.
  - Support system: Handover, Access Control, and Settings.
  - Reference: Platform, System Architecture, Engineering, Getting Started, Guide, and Devotional.
- Current item uses weight, a slim rail, border, and surface change rather than colour alone.
- Persistent compact feedback and source-reference group.

### Header

- Skip link.
- Drawer trigger.
- Chapter number, navigation-group label, and page title.
- Optional page-context music control.
- Access-mode status and sign-out action.
- Language, sound, and appearance controls grouped as a compact dock.

### Main canvas

- Maximum content width of 1440 pixels.
- Page context spine precedes route content.
- Route-specific class and data attributes allow page and mode styling without separate layouts.
- No shared footer is rendered.

## Adaptive shell

Breakpoint: `900px`.

- Header becomes a one-line compact bar.
- Desktop utility controls move into the secondary drawer except for the page music trigger.
- Fixed bottom navigation exposes Dashboard, Rosters, Prefects, and More.
- More opens the same shared navigation and utility groups.
- Safe-area padding protects the final page action and bottom navigation.
- Tables use alternate card or grid presentations from the same display model.
- Phone landscape remains in the adaptive shell.

The adaptive rules are implemented in:

- [`nicegui_app/assets/css/sing-yin-mobile-v1.css`](../../nicegui_app/assets/css/sing-yin-mobile-v1.css)
- [`nicegui_app/assets/css/sing-yin-theme-v1.css`](../../nicegui_app/assets/css/sing-yin-theme-v1.css)
- [`nicegui_app/assets/css/sing-yin-narrative-v1.css`](../../nicegui_app/assets/css/sing-yin-narrative-v1.css)

## Page-local reference layout

Source: [`nicegui_app/ui/reference_navigation.py`](../../nicegui_app/ui/reference_navigation.py)

- `render_page_toc` provides a compact on-page contents list.
- `render_reference_pager` creates explicit previous and next reading order.
- These helpers are used by onboarding, guide, handover, platform, engineering, and architecture pages.

## Layout dependencies

- Theme application: [`nicegui_app/ui/theme.py`](../../nicegui_app/ui/theme.py)
- Translation and locale: [`nicegui_app/ui/i18n.py`](../../nicegui_app/ui/i18n.py)
- Browser preferences: [`nicegui_app/ui/preferences.py`](../../nicegui_app/ui/preferences.py)
- Page music: [`nicegui_app/ui/music.py`](../../nicegui_app/ui/music.py)
- Semantic feedback sound: [`nicegui_app/ui/sound.py`](../../nicegui_app/ui/sound.py)
- Current page and access context: [`nicegui_app/runtime.py`](../../nicegui_app/runtime.py)
- Contact destinations: [`nicegui_app/contact.py`](../../nicegui_app/contact.py)

## Design invariants

- Main content precedes repeated mobile navigation in DOM order.
- All primary main-content actions retain a practical touch target.
- Appearance and sound changes preserve the current route and unfinished form context.
- Language changes may reload only after the dirty-form guard is satisfied.
- Global status banners share one ordered stack.
- Context imagery never owns required information or sits behind operational tables and forms.
