# Content Design Audit

**Owner:** `Professional_Design_System.md` content-design contract

**Scope:** Public entrance, unified Admin／Guest workbench, Viewer and support

**Baseline:** live `v1.2.0-rc.21`; candidate source must be verified separately

This is the decision record for non-obvious runtime-copy changes. It does not replace the complete Operator Guide, architecture, security or release documentation. Counts below are representative first-render observations from source inspection and the live rc21 desktop／390px evidence; conditional error, confirmation and recovery copy is intentionally excluded until its state is active.

## Inventory and disposition

| Route／component | Copy owner | Audience | Purpose | Baseline classification | Action and deletion consequence |
|---|---|---|---|---|---|
| Public `/` proposition | Worker `PORTAL_HTML` | Public | Choose Admin or Guest／understand shares | Required but repeated by kicker, workflow cue and access-panel reassurance | Keep one proposition and both CTAs; remove decorative kicker and duplicate workflow cue. No loss because the same workflow becomes visible after entry. |
| Public `/` devotional | Worker `PORTAL_HTML` | Public | Begin service reflectively | Required sacred content | Keep Scripture, references, reflection and refresh; do not compress it into marketing copy. |
| Dashboard Daily Verse | `foundation.py`／`home.py` | Admin／Guest | Read, reflect, return to work | Required sacred content | Keep compact reading and reflection disclosure. |
| Dashboard Weekly Pulse | `media.py`／`home.py` | Admin／Guest | Identify stage and next action | Helpful but introductory sentence restates visible steps | Remove the repeated sequence sentence; keep state badge, step labels and current action. |
| Dashboard history | `home.py` | Admin／Guest | Resume recent work | Helpful | Keep count, states and actions; remove only prose that restates the list. |
| `/rosters` page lead | `weekly.py` | Admin／Guest | Identify page and persistence | Duplicated／misplaced | Shell already owns H1; remove duplicate title and generic persistence line. Keep storage lifecycle and all publication／fairness consequences at the decision point. |
| Roster workflow hints | weekly catalog／components | Admin／Guest | Prevent policy mistakes | Required where contextual | Retain role, availability, publication, withdrawal, absence and recovery consequences; remove only state explanations already encoded by current／completed／locked steps. |
| `/prefects` page lead | `people.py` | Admin／Guest | Add or review prefects | Title duplicated; action required | Remove repeated title and keep `新增導學風紀` as the dominant action. |
| Prefect import | `importing.py`／`people.py` | Admin; restricted Guest | Parse, map, preview, write | Helpful but front-loaded | Keep format／size constraints beside upload; move long mapping／AI detail to contextual disclosure. |
| Fairness report downloads | `reporting.py`／`people.py` | Admin／Guest demo | Choose report period and output | Required; intro and badge repeat read-only nature | Keep period selectors, output meaning and JSON-not-backup warning; remove duplicate reassurance. |
| `/settings` page title and handover card | `stewardship.py` | Admin／Guest | Manage audio, custody and recovery | Duplicate H1 and repeated handover intro | Remove repeated title and intro; keep scope, readiness truth, database／backup evidence and recovery actions. |
| `/handover` | stewardship catalog／route | Admin／Guest demo | Transfer custody without losing evidence | Required, some narrative duplication | Keep numbered procedure and destructive rollover consequence; use TOC／disclosure for evidence detail. |
| `/platform` hero | platform catalog／`showcase.py` | All workbench modes | Explain purpose and ownership | Required but product lockup + kicker + H1 + principle compete | Keep product lockup, H1 and one first-person summary; remove decorative kicker and repeated slogan. |
| `/engineering` hero | platform catalog／`showcase.py` | All workbench modes | Inspect current evidence | Required but kicker／badge repeat evidence state | Keep H1, one summary and actual filterable evidence; remove generic kicker and promotional badge. |
| `/system-architecture` hero | platform catalog／`showcase.py` | All workbench modes | Locate boundary and recovery evidence | Required but five adjacent orientation elements | Keep H1, one summary, real state and precise destination; remove kicker and reading notes that repeat the TOC. |
| `/guide`／`/getting-started` | stewardship catalog／`home.py` | Successor／operator | Complete a task or find recovery | Helpful; some page-title duplication | Keep task groups, first action and troubleshooting; let shell own H1 and use short decision-changing leads only. |
| `/devotional` | foundation catalog／`home.py` | All workbench modes | Read → reflect → pray → serve | Required sacred content | Preserve Scripture, attribution, reflection and prayer; remove only redundant page-purpose scaffolding. |
| NiceGUI `/support` core | support catalog／route | Admin／Guest | Describe reproducible incident | Required | Show Expected, Actual and Steps first. Infer page/action; disclose optional diagnostics and attachments. |
| NiceGUI `/support` follow-up | support route／JS | Admin／Guest | Save or carry report | Initially competing | Show one Preview／Build action first; reveal Download／Copy／Email only after a report exists. |
| Public `/support` | Worker support constants | Public／Viewer | Build non-persistent report | Required but safety and optional metadata front-loaded | Keep three core fields first; disclose category, impact and concise exclusions; reveal output actions after build. |
| `/view` | Worker Viewer | Viewer | Read approved roster | Required and already focused | Keep silent read-only roster, expiry, latest-link guidance and one support link. |

## Representative baseline and target

| Surface | Baseline first-view competition | Target |
|---|---|---|
| Public entrance | proposition + kicker + two CTA sets + workflow cue + access reassurance | one proposition; Admin and Guest choices immediately visible; devotional follows without another workflow lecture |
| Dashboard | Daily Verse + next action + workflow intro + three states + history intro | Daily Verse; one next action; visible stage model; compact history |
| Rosters | shell H1 + repeated H2 + persistence sentence before workflow | shell H1 followed by lifecycle／workflow and the current task |
| Platform | brand lockup + kicker + H1 + intro + principle before evidence | brand lockup + H1 + one summary, then scannable evidence |
| Engineering | kicker + H1 + intro + generic verified badge before actual evidence | H1 + one summary, then current evidence／filters |
| Architecture | kicker + H1 + intro + badge + two reading notes + CTA | H1 + one summary + real state + optional destination |
| Support | page intro + mode status + explanation + seven fields + attachments + several actions | three core fields + one action; optional detail disclosed; contextual result actions |

## Content that must remain visible when active

- publication, withdrawal, fairness reconciliation, restore and new-year rollover consequences;
- Guest restrictions that change an available action;
- form labels, correction text, consent, attachment limits and privacy exclusions;
- OP／REQ references needed for recovery;
- Scripture translation attribution and Chinese-name authority;
- Viewer read-only／expiry truth and the latest-link instruction;
- loading, empty, error, success and conflict states with one safe next action.

## Review rule

Each future runtime paragraph must name its decision-changing job in review. If that job already belongs to the shell, control label, state marker, confirmation or documentation, the duplicate is removed rather than rephrased. Automated tests protect hierarchy, capability and recovery contracts; they do not enforce arbitrary word counts.
