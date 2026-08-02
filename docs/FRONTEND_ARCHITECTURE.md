# 前端架構與迭代契約 / Frontend architecture and iteration contract

**Status:** Active

**Owner:** `Professional_Design_System.md` owns product intent and design language; this document owns frontend composition, implementation seams and migration rules.

**Scope:** Public Worker entrance, NiceGUI application shell, shared components, route families, responsive behaviour and motion.

## Product frame

Service Weave is a single-institution, local-first school duty-operations platform. Its principal user prepares and verifies a weekly duty roster under time pressure. Teacher advisors and successors inspect evidence and handover material. Guests exercise the same visible workflow with fictional, non-persistent data.

The frontend therefore optimises for:

- recognition of the current stage and next safe action;
- fast repeated operation, not dashboard spectacle;
- credible fairness, recovery and handover evidence;
- complete Admin/Guest visual parity with server-enforced capability boundaries;
- Traditional Chinese first, complete English parity;
- usable keyboard, touch, reduced-motion, forced-colours and 256 CSS-pixel reflow states.

## Authority and implementation map

| Concern | Authoritative source | Verification owner |
|---|---|---|
| Product paradigm, visual hierarchy, tokens and motion principles | `Professional_Design_System.md` | token, accessibility and design-contract tests |
| Composition, route-family ownership and migration policy | this document | architecture and component-contract tests |
| Shared shell DOM and viewport runtime | `nicegui_app/ui/shell.py` | `verify_nicegui_mobile.py`, `verify_nicegui_ui.py` |
| CSS loading order | `nicegui_app/ui/theme_markup.py` | `test_ui_component_contract.py` |
| Canonical reset composition | `nicegui_app/assets/css/sing-yin-command-center-v2.css` | light/dark desktop/mobile browser evidence |
| Dashboard task order | `nicegui_app/ui/page_routes/home.py` | `test_dashboard_information_architecture.py` |
| Public entry composition and state | `cloudflare/roster_viewer/worker.js` | Deno Worker contracts and staged-browser smoke |
| Semantic icon lifecycle | existing shared motion runtime and inventory | motion contracts and semantic browser verifier |

No CSS file, page route or animation runtime may become an owner for authentication, capability, roster policy, persistence, transaction, recovery or deployment behaviour.

## Layer ownership

| Layer | Owns | Must not own |
|---|---|---|
| `tokens` | primitive and semantic values generated from the token contract | page selectors or one-off values |
| `base` | reset, typography and document defaults | route composition |
| `layout` | shell primitives and content geometry | visual stories |
| `compatibility-*` | unmigrated rc-era selectors | new product decisions |
| `components` | reusable controls, surfaces and states | route-specific placement |
| `narrative` | approved atmosphere and devotional treatments | forms, tables or student data |
| `interaction` | tactile, focus and pointer feedback | business state |
| `motion` | semantic icon and lifecycle contracts | perpetual decoration |
| `mobile` | legacy narrow-screen adaptations | desktop defaults |
| `command-center-v2` | canonical reset composition and responsive overrides | managed token redeclaration or backend behaviour |

`command-center-v2` is the sole terminal composition layer and must load last. It is a bounded migration seam for resetting a large, mature frontend without copying old page rules into every route. When a v2 rule becomes stable and independent of composition, move it into the appropriate lower owner, delete the superseded compatibility rule and preserve before/after browser evidence. A second terminal layer is prohibited.

## Shared composition contracts

### Application shell

- Desktop navigation is a `264px` institutional rail; the main canvas uses the remaining viewport. The compact `64px` header contains route identity and global controls only.
- Routine support links are compact and secondary; full explanation lives on `/support` and in documentation.
- Shell atmosphere is an `84px` contextual band. It never competes with the page task.
- Visual-viewport keyboard mode is enabled only when a focused editable control and a material viewport reduction are both present.

### Dashboard

- The workflow command surface is first in DOM and visual order.
- The current step owns the strongest action treatment.
- Recent roster history is a compact review rail.
- Daily Verse follows as an editorial band and remains directly reachable as a full page.
- No synthetic KPI, user count, progress percentage or alert is permitted.

### Operational routes

- Tables and forms use solid, high-contrast surfaces.
- One route has one dominant task; secondary evidence uses expansions, side rails or progressive disclosure.
- Consequential actions state the result and recovery path before confirmation.
- Waiting UI reports real busy state, phase or measured progress; it never delays completion to display animation.

### Settings and recovery

- Readiness／handover state is the first working surface so an operator sees missing custody evidence before changing preferences.
- Preferences and media use the action role; persistence and handover-package controls use the continuity role; restore uses the attention role and retains its separate danger confirmation.
- These roles are shared structural classes in the sole terminal layer. Individual settings panels may not create a competing radius, shadow or colour grammar.
- Reordering presentation must not reorder callbacks, relax confirmation, trigger expensive verification twice or change Admin／Guest capabilities.

### Public entrance

- One visible Admin entry and one visible Guest entry per viewport.
- The secure Cloudflare Access and bounded Guest contracts remain unchanged.
- Desktop presents identity, a concise value statement, the three-step product explanation and the entry choice as one composition.
- Mobile presents one decision-first stack: concise identity and value, then one Admin／Guest action pair. A second administrator heading may remain in the accessibility tree for labelled support content but is visually clipped, not shown as a duplicate card.
- Mobile supporting order is Daily Verse → welcome music → sign-in help → sharing／feedback. These remain available without competing with the entry decision.

## Motion and dependency policy

CSS owns immediate hover, focus, press and reduced-motion fallbacks. The vendored GSAP Core runtime may coordinate bounded semantic sequences after the interface is usable. Animation code must use transform and opacity, kill replaced timelines, clean up on navigation/reconnect and stop while disabled or busy. ScrollTrigger, framework adapters and extra plugins are not installed unless a measured interaction cannot be implemented accessibly with the existing runtime.

## Change protocol

1. Identify the operator problem and measurable improvement.
2. Change the design-system contract before introducing a new visual grammar.
3. Prefer a shared selector/component over a page-local fork.
4. Preserve route, data, identity, Guest and recovery contracts unless a separate backend change is approved.
5. Verify one representative page family first, then migrate siblings.
6. Capture light/dark and desktop/mobile evidence; include keyboard and reduced-motion checks for changed interactions.
7. Update this document whenever layer ownership, composition order, responsive behaviour or frontend dependencies change.
8. Update status, changelog and acceptance evidence with the exact commit and deployed version; never turn candidate evidence into a live claim.

## Definition of done

A frontend change is done when it is visually coherent, functionally truthful, responsive, accessible, documented, covered by proportionate tests and verified against the exact release candidate. A screenshot alone is not completion; neither is a green unit suite without rendered evidence. Production completion additionally requires exact-source deployment, canonical smoke and truthful status generation.
