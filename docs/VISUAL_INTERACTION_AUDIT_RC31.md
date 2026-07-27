# rc31 visual and interaction defect inventory

This inventory records the evidence-led scope for the binary-appearance and
header-control release. It describes the rc30 starting point; it is not proof
that rc31 is deployed. The release report and production browser evidence are
the authority for the final state.

| Surface／route | Context checked | Observable rc30 defect | Shared owner and rc31 decision | Verification |
|---|---|---|---|---|
| NiceGUI workbench header／all routes | Admin and Guest; desktop; zh-HK／en; Light／Dark | Language alone has a visible framed surface; sound and appearance suppress the same edge／shadow; logout has separate geometry. | `shell.py` emits one `sy-header-control` family. Theme CSS owns rest, focus, hover, press, selected, disabled and danger variation. | Computed border, surface, radius, target and focus styles for all four siblings in both themes. |
| NiceGUI appearance control／all routes | Desktop; explicit and unset preferences | A compact button opens a three-choice menu and its icon describes the stored preference rather than the resolved appearance. | Replace with one binary button. `system` is initialization only; first activation stores the opposite resolved mode. | Light → Dark → Light; system-resolved first click; reload, navigation and two-context persistence. |
| Mobile drawer／all routes | 256／320／390／412px; portrait／landscape; touch; reduced motion | A full-width three-radio field consumes space and creates a second component grammar. | Replace the fieldset with the same single button family in the Quick settings grid; retain a visible action label. | One visible mobile button, no radio／fieldset, 44px target, drawer keyboard/touch behavior and no overflow. |
| Public entrance and encrypted Viewer | 320／390／768／1440px; Light／Dark／system | `<select>` exposes three states, differs from the workbench and does not tell the next action. | One native button with current sun／moon icon, next-action bilingual label, explicit persistence and OS listener while unset. | Worker contract plus Chromium click, reload, system-change, keyboard, reduced-motion and no-store Viewer flow. |
| Header glyph feedback／all workbench routes | Sound on／off; theme change; keyboard／touch | Icons update, but sibling controls do not share a state-animation contract or pressed state. | Add synchronized `aria-pressed`／state attributes and bounded icon transition; fixed host geometry. | Icon／ARIA synchronization, no layout shift, reduced-motion static result. |
| Logout／Admin and Guest | Success, failure, browser back | Session action looks unlike sibling controls; visual styling risks reading as an ordinary toggle. | Shared frame with `logout` semantic variation; retain existing backend revocation and destination behavior. | Existing auth tests plus focused rendered activation and browser-back check. |
| Sidebar, bottom navigation and route content | Dashboard, rosters, prefects, adjustments, audit, settings, support, guide, platform, architecture, engineering | No evidence that the reported defect requires page redesign; broad edits would add risk without benefit. | Keep stable composition. Audit only for leaked theme selectors, clipped tools, duplicate CSS and contrast regressions. | Route matrix, console/page errors, overflow, forced colours and representative screenshots. |
| Busy／disabled／error states | workbench and public surfaces | Existing state rules are distributed; the header family does not explicitly inherit them. | Shared control owner prevents duplicate activation, preserves focus and makes busy／disabled state visible without layout change. | Source contract plus fixture and rendered state checks. |

## Rejected expansion

- No new image, animation runtime, page layout or backend workflow is introduced;
  none is needed to solve the confirmed control-state defect.
- Existing Guest capability, storage, AI／upload restrictions and roster policy
  remain unchanged; visual consolidation is not an authorization boundary.
- Historical rc30 screenshots, deployment reports and evidence remain historical
  and are not rewritten as rc31 proof.

## Source-candidate evidence

- `python -X utf8 -m pytest -q`: 901／901 passed.
- `scripts/verify_rc31_theme_controls.py`: 8／8 isolated Chromium cases passed
  across Admin／Guest, desktop／mobile and OS-light／OS-dark initialization,
  producing 24 temporary screenshots with no console, page or server errors.
- The Worker contract suite remains 46／46. The rc31 browser matrix is registered
  as the formal release verifier's fifteenth fingerprint-bound gate.
- These checks prove the working-tree candidate only. They do not claim a
  protected-main merge, annotated tag, Windows origin deployment, Worker
  promotion or supervised human acceptance.
