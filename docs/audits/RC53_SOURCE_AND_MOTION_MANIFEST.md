# rc53 source, interaction and motion manifest

**Status:** candidate implementation contract; not production evidence.

## Source boundary

- Baseline branch: `origin/main` at `27645627a8793adbd2f74e8a1e294e85bf6b3dd1`.
- Candidate branch: `codex/rc53-spreadsheet-prefect-motion` in the isolated worktree `D:\codex-worktrees\rc53-spreadsheet-prefect-motion`.
- Excluded from this candidate: `D:\code_v3`, the `1ab2` worktree, old rc32 material, user screenshots, runtime databases, backups, logs, generated downloads and local secrets.
- Production status remains owned by `docs/status/current-release.json` and must be re-verified from Git, the scheduled-task bundle, SQLite schema and Cloudflare before release.

## Interaction matrix

| Surface | Pointer | Touch | Keyboard | Persistence |
|---|---|---|---|---|
| Draft cell | click to edit; drag after 8px to move/swap | select source, then destination | roving arrows; Enter/F2 edit; Space move; Escape cancel | one versioned batch with stable command ID |
| Slot state | explicit close/reopen action | same explicit action | Enter/Space on labelled action | `roster_slot_exceptions`; blank never means closed |
| Prefect row | direct low-risk field editing | same fields in one-column card | native field navigation | row-level CAS and command receipt |
| Identity/role/archive | confirmation dialog | confirmation dialog | trapped dialog focus | existing audited transaction |

## Inline prefect field matrix

| Inline | Confirmation dialog only |
|---|---|
| English name, form, class, available weekdays, mentoring support, fixed general duty, remarks | Chinese name, role, fairness history, archive/lifecycle state |

Every editable row is keyed by immutable prefect ID and retains its original version. A conflict preserves local input, shows the latest server version, and offers either latest data or a reviewed reapply. Silent overwrite is prohibited.

## Canonical roster states

| Stable code | Traditional Chinese | English | Meaning |
|---|---|---|---|
| `assigned` | 已安排 | Assigned | A named prefect occupies the cell. |
| `vacant` | 空缺（待安排） | Vacant | Duty is required but no prefect is assigned. |
| `room_closed` | 不開放 | Closed | Fixed policy closes this room/slot. |
| `unavailable` | 不開放 | Unavailable | Operator closes this one weekly cell. |
| `day_closed` | 全天不開放 | Closed all day | The complete weekday is closed. |

Precedence: `day_closed > room_closed > unavailable > assigned/vacant`.

## Motion-source decisions

| Source | Decision | Local contract |
|---|---|---|
| `transitions.dev` | adapt concepts only | State copy, icon, dialog, accordion and skeleton may transition with the existing CSS/GSAP lifecycle owner; no copied source. |
| `thinking-orbs` | reject as a general workbench loader | Ordinary database work uses the native indeterminate progress indicator. AI schema suggestion may use the same truthful busy state, but is not given a decorative or misleading thinking animation. |
| `border-beam` | adapt narrowly | A verified boundary may receive one short completion transition; no permanent loop, rainbow treatment or second runtime. |
| `metal-fx` | reject | React/WebGL and a persistent shader budget do not fit this local NiceGUI operations workstation. |

Unknown duration is always indeterminate. The operation starts immediately; the dialog appears only when the existing reveal threshold is crossed. Completion is never delayed for animation, and no fabricated percentage or fabricated phase rail is shown.

## Lifecycle ownership

The existing motion runtime is the only JavaScript animation owner. It must pause when hidden/offscreen, respect reduced motion and forced colours, and dispose listeners, observers, RAF callbacks and timelines on route teardown. No React, AG Grid, handcrafted SVG art or additional animation runtime is introduced by rc53.
