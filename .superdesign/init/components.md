# Components — current NiceGUI source inventory

Generated from the authoritative repository checkout on 2026-07-30. This is a source-grounded map for design exploration, not a second component specification.

## Runtime

- NiceGUI + Quasar only; do not introduce React, Tailwind, Radix, Framer Motion, or copied community runtime code.
- Material outlined icon names are passed through NiceGUI.
- Traditional Chinese is primary; English uses the same DOM hierarchy.
- Admin and Guest render the same component skeleton. Capability checks remain server-side.

## Public component API

Canonical source: `nicegui_app/ui/components.py` (complete file, 406 lines).

Source outline (python):
    ActionVariant = Literal["primary", "secondary", "quiet", "attention", "danger"]
    IconStoryCategory = Literal["preview", "persistent", "lifecycle", "static"]
    StatusTone = Literal["action", "stable", "attention", "danger", "neutral"]
    WorkflowState = Literal["active", "done", "pending"]

    def action(text: str, *, icon: str | None = None,
               on_click: Callable[..., object] | None = None,
               variant: ActionVariant = "primary", busy: bool = False,
               disabled: bool = False, test_id: str | None = None,
               classes: str = "", motion_role: str | None = None,
               icon_story_to: str | None = None,
               icon_story_category: IconStoryCategory | None = None): ...

    def field(*, label: str, control_factory: Callable[[], _Control],
              description: str | None = None, optional: bool = False,
              error: str | None = None, read_only: bool = False,
              test_id: str | None = None) -> _Control: ...

    def status(text: str, tone: StatusTone = "neutral", *, props: str = ""): ...
    def dialog(*, title: str, description: str, consequence: str | None = None,
               persistent: bool = False, test_id: str | None = None): ...
    def empty_state(*, title: str, body: str, icon: str,
                    action_text: str | None = None,
                    on_action: Callable[..., object] | None = None,
                    action_variant: ActionVariant = "secondary",
                    action_test_id: str | None = None,
                    illustrated: bool = False, test_id: str | None = None) -> None: ...
    def restricted_state(*, title: str, body: str,
                         action_text: str | None = None,
                         on_action: Callable[..., object] | None = None,
                         test_id: str | None = None) -> None: ...
    def progress_state(*, title: str, status_text: str,
                       value: float | None = None,
                       test_id: str | None = None) -> None: ...
    def responsive_table(*, rows: list[dict[str, object]],
                         columns: list[dict[str, object]], row_key: str,
                         classes: str = "", test_id: str | None = None) -> None: ...
    def workflow_step(*, number: int, title: str, detail: str,
                      state: WorkflowState, state_text: str, icon: str,
                      action_text: str | None = None,
                      on_action: Callable[..., object] | None = None) -> None: ...
    def editorial_heading(*, title: str, copy: str,
                          kicker: str | None = None,
                          anchor_id: str | None = None) -> None: ...
    def page_toc(items: Sequence[ReferenceItem]) -> None: ...
    def reference_pager(*, previous: ReferenceDestination | None = None,
                        next_: ReferenceDestination | None = None) -> None: ...
    def code_sample(*, code: str, label: str, language: str = "text",
                    test_id: str | None = None) -> None: ...

Every public primitive owns complete default, hover/focus, disabled, busy, error, empty, and restricted semantics. `action` accepts semantic icon-story metadata; animation must not alter button hit geometry.

## Existing feature renderers

Canonical source: `nicegui_app/ui/page_shared.py`.

| Renderer | Source range | Responsibility |
|---|---:|---|
| operation hint | search `_render_operation_hint` | purpose + method before consequential work |
| roster presentation | search `_render_roster_table` and mobile card renderer | shared duty data on desktop and phone |
| honest progress | search `_run_with_progress` | prevents duplicate durable actions |
| storage lifecycle | search `_render_storage_lifecycle` | draft/publish/adjust/backup explanation |
| safe route state | search `_render_roster_route_state` | stale and premature URL recovery |
| co-creation | search `_render_co_creation` | creator/project close, non-operational |

## Interaction contract

- Whole-button state may morph icon + label + surface, but layout cannot jump.
- Persistent state changes (save, publish, withdraw) need a reversible or explicit completion state.
- Preview-only hover stories reset on pointer leave and never imply completion.
- Touch, keyboard, reduced-motion, forced-colours, busy, and disabled states remain fully legible.
- No decorative animation behind tables, names, fairness data, warnings, or PDF content.
