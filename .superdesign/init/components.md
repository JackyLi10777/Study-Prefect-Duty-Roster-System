# Shared UI Components

This is a source-linked inventory for the NiceGUI application. The canonical implementation remains in the linked Python and CSS files; this document intentionally does not duplicate large source files.

## Rendering stack

- Framework: NiceGUI with its Vue and Quasar browser runtime.
- Component library: NiceGUI `ui.*` builders and Quasar controls.
- Icons: Material icon names supplied through NiceGUI.
- Styling: semantic `sy-*` classes, generated CSS variables, Quasar properties, and utility classes passed through `.classes()`.
- Translation: Traditional Chinese first, with complete English messages resolved at render time.

The highest-use framework primitives are `label`, `element`, `button`, `row`, `column`, `icon`, `card`, `select`, `dialog`, `tabs`, `table`, and `expansion`.

## Shared primitives

| Component or pattern | Canonical source | Purpose | Important inputs |
|---|---|---|---|
| Progress operation dialog | [`_run_with_progress`](../../nicegui_app/ui/page_shared.py) | Presents an honest indeterminate operation, records the outcome, and prevents duplicate durable actions. | title key, working key, icon, callable |
| Feedback channel | [`_render_feedback_channel`](../../nicegui_app/ui/page_shared.py) | Shared support and source-reference panel in full or compact form. | `compact` |
| Tone badge | [`_tone_badge`](../../nicegui_app/ui/page_shared.py) | Stable semantic status vocabulary across action, stable, attention, danger, and neutral states. | text, tone, optional properties |
| Responsive table | [`_render_responsive_table`](../../nicegui_app/ui/page_shared.py) | Renders one display model as a desktop table and a labelled phone grid. | rows, columns, row key, class, test identifier |
| Roster table and cards | [`_render_roster_table`](../../nicegui_app/ui/page_shared.py) | Shared wide table and phone duty-card representation. | roster identifier |
| Mobile roster cards | [`_render_mobile_roster_cards`](../../nicegui_app/ui/page_shared.py) | Day-grouped duty cards without horizontal scrolling. | abstract display rows |
| Mobile directory cards | [`_render_mobile_prefect_cards`](../../nicegui_app/ui/page_shared.py) | Compact identity, role, availability, and fairness summary cards. | abstract display rows |
| Weekly flow step | [`_render_flow_step`](../../nicegui_app/ui/page_shared.py) | One numbered stage in the generate, review, and adjustment sequence. | number, title, detail, state, icon, optional action |
| Storage lifecycle | [`_render_storage_lifecycle`](../../nicegui_app/ui/page_shared.py) | Explains draft, publication, adjustment, and verified recovery state. | workflow read model |
| Operation hint | [`_render_operation_hint`](../../nicegui_app/ui/page_shared.py) | Concise purpose-and-method cue immediately before a consequential action. | body key, icon |
| Empty state | [`_render_empty_state`](../../nicegui_app/ui/page_shared.py) | Clear next action for an empty result, with an optional contextual illustration slot. | title, body, icon, optional action |
| Route recovery state | [`_render_roster_route_state`](../../nicegui_app/ui/page_shared.py) | Safe recovery choices for stale or premature roster URLs. | copy keys, icon, primary and secondary routes |
| Co-creation panel | [`_render_co_creation`](../../nicegui_app/ui/page_shared.py) | Shared non-sensitive creator and project-closing surface. | translated content from the catalogue |
| Page contents navigation | [`render_page_toc`](../../nicegui_app/ui/reference_navigation.py) | Compact page-local anchor navigation. | ordered anchor and label pairs |
| Reference pager | [`render_reference_pager`](../../nicegui_app/ui/reference_navigation.py) | Previous and next navigation within an operator or trust reading lane. | previous and next destinations |
| Restricted capability | [`render_restricted_capability`](../../nicegui_app/ui/page_access.py) | Shared explanation for an unavailable action without treating UI as the permission boundary. | icon |

## Stateful feature components

These are reusable renderers, but their visual state is coupled to workflow or browser state.

| Component | Canonical source | Visual states |
|---|---|---|
| Page music control | [`render_page_music_control`](../../nicegui_app/ui/music.py) | playing, paused, browser-blocked, off; volume and profile controls |
| Music settings | [`render_music_library_settings`](../../nicegui_app/ui/music.py) | catalogue, local additions, context assignments, sound preferences |
| Guest music settings | [`render_guest_music_settings`](../../nicegui_app/ui/music.py) | bounded settings without official-write controls |
| Online music panel | [`render_youtube_panel`](../../nicegui_app/ui/youtube_music.py) | guidance, saved public playlist, search results, visible player |
| Access-control console | [`render_access_control_console`](../../nicegui_app/ui/access_control.py) | restricted, unconfigured, ready, empty, loading, and active-link management |
| Published-roster share action | [`render_roster_share_action`](../../nicegui_app/ui/access_control.py) | unavailable, confirmation, receipt, and revoke states |

## Common visual class families

- Surfaces: `sy-surface`, `sy-surface-subtle`, `sy-workbench`.
- Status: `sy-status-badge`, `sy-tone-*`, `sy-status-stack`.
- Navigation: `sy-sidebar`, `sy-nav-active`, `sy-mobile-tabbar`, `sy-reference-*`.
- Forms and consequences: `sy-adjustment-*`, `sy-mobile-actions`, `sy-border-attention`.
- Empty and recovery states: `sy-empty-state`, `sy-inline-empty`, `sy-restricted-state`.
- Editorial contexts: `sy-daily-start`, `sy-chapel`, `sy-handover-*`, `sy-platform-*`, `sy-engineering-*`, `sy-architecture-*`.

## Context rules

- Include the linked Python renderer, the shared shell, the relevant route module, and the four theme stylesheets for visual work.
- Include the relevant translation catalogue when exact bilingual copy structure matters.
- Use abstract fixture values when a draft needs rows, names, dates, counts, or status examples.
- Treat services and policy packages as state contracts. They are not visual components and should be added only when a design depends on their state vocabulary.
