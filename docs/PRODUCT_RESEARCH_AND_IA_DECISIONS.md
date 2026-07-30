# Product Research and Information-Architecture Decisions

**Product:** Service Weave／服事經緯 — 聖言中學導學風紀值班表生成系統

**Decision version:** 1.1

**Last reviewed:** 2026-07-30
**Owner:** `Professional_Design_System.md` defines the executable design direction; this document records why that direction was chosen.

## Decision summary

The product uses one **Institutional Operations Product** with four deliberately different zones:

1. **Public Product Entrance** — explain purpose, trust boundary and the choice between Guest and Admin.
2. **Unified Operations Workbench** — complete the weekly sequence: generate → review／publish／export → published-duty absence adjustment.
3. **Trust & Engineering Hub** — show verified architecture, fairness, release and recovery evidence without inventing corporate claims.
4. **Documentation and Developer Portal** — route operators, successors and maintainers to task-based guidance and reference material.

Admin is the canonical product. Guest uses the same routes, page definitions and component grammar, but a bounded fictional-data adapter and server-enforced deny-by-default capabilities. The interface may explain a restriction; it never acts as the security boundary.

The visual direction has evolved to **Luminous Sacred Precision／明澈而莊重的精準感**. It retains Quiet Precision's editorial hierarchy, solid accessible operational surfaces and purposeful motion, then adds a narrowly governed luminous edge and Service Weave continuity line to navigation, transient choices and verified progress. Site-wide Neumorphism, persistent blur, glass behind operational data, decorative animation and card-heavy dashboard imitation remain rejected.

### Browser media-policy decision — Adopt／Adapt／Reject

- **Adopt:** treat the resolved `HTMLMediaElement.play()` promise or a trustworthy `playing` event as the only evidence that sound started; classify `NotAllowedError` separately from transport, decode and lifecycle failures.
- **Adapt:** attempt same-origin welcome music once. With no explicit entry-sound choice, the Administrator／Guest CTA itself is the trusted default-music retry and calls `play()` synchronously; success, rejection, synchronous failure or a bounded startup timeout all continue exactly once to the selected identity. **Default: Enter with music** and **Continue quietly** are optional preference／recovery controls, not a gate.
- **Reject:** forced-autoplay claims, muted-start deception, arbitrary first-click capture listeners, repeated hidden retries, third-party autoplay and any server header presented as a way to bypass browser policy.

`Permissions-Policy: autoplay=(self)` documents the intended same-origin boundary but does not override the browser's user-activation policy. The encrypted Viewer remains silent.

### Waiting-state decision — Adopt／Adapt／Reject

- **Adopt:** expose a real busy state immediately, prevent duplicate activation, preserve the initiating context, and announce only meaningful phase changes. An indeterminate operation does not expose `aria-valuenow`; a determinate bar is allowed only when the service owns a real `completed／total` measurement.
- **Adapt:** use the existing public-entry controller and NiceGUI progress dialog as the two shared owners. Entry navigation receives role-specific Admin／Guest copy and a delayed indeterminate track; consequential local work receives a persistent bilingual phase dialog. Fast work is never slowed merely to display animation.
- **Reject:** decorative looping loaders, fictional percentages, page-local spinner dialects, an enabled retry for a write whose outcome is unknown, skeletons for unknown content shapes, and any music-loading state presented as authentication progress.

The accessible contract follows the WAI-ARIA [`progressbar` role](https://www.w3.org/TR/wai-aria-1.2/#progressbar): determinate values are bounded and truthful; indeterminate progress omits a value. Reduced motion retains labels, boundaries and busy semantics without moving sheen, scale or rotation.

## Research method

Each reference was reviewed for a specific product problem. A pattern is adopted only when it reduces operator effort, improves evidence or strengthens a boundary. “Adapt” means the underlying logic is retained but rewritten for a small, local-first school workflow. No reference code, trade dress, product copy or brand asset is copied.

| Source (official or primary) | Accessed | Observed pattern | Decision | Product adaptation | Risk／rejection boundary |
|---|---:|---|---|---|---|
| [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines) | 2026-07-26 | Hierarchy, consistency, adaptable layout and accessibility are treated as system qualities. | **Adapt** | Use stable geometry, strong type hierarchy, predictable focus and device-aware reflow. | Do not imitate Apple screens, SF Symbols, Liquid Glass or platform-specific chrome. |
| [OpenAI About](https://openai.com/about/), [Business](https://openai.com/business/) and [News](https://openai.com/news/) | 2026-07-26 | Mission-first editorial reading, outcome-led explanation and evidence indexes with category/date. | **Adapt** | Public entrance explains purpose first; Platform explains solution and boundary; Engineering uses evidence lists and filters. | Reject chat-box imitation, sales funnel, pricing language, news-card cloning and OpenAI visual assets. |
| [Cloudflare Developer Docs](https://developers.cloudflare.com/) | 2026-07-26 | Separate “get started”, task guidance, reference architecture, product directory and changelog. | **Adopt selectively** | Documentation portal separates operator journeys from architecture, security and release reference. | Do not expose a fictional public API or place every technical category in the operator navigation. |
| [Cloudflare Trust Hub](https://www.cloudflare.com/trust-hub/) | 2026-07-26 | Trust claims are grouped by privacy, technology, compliance and transparency, with evidence paths. | **Adapt** | Trust Hub groups identity, data lifecycle, fairness, backup/recovery and release evidence; every claim links to an owner or verifier. | No certification badges, customer-logo wall or enterprise claims the project cannot prove. |
| [GitLab Docs](https://docs.gitlab.com/) | 2026-07-26 | Search-first entry, workflow-based “get started”, administration, reference architecture and contribution paths are separated. | **Adapt** | Starting routes are grouped by reader and task; engineering material remains outside the weekly workbench. | Reject GitLab-scale module taxonomy and reference architectures for thousands of users. |
| [Linear Start Guide](https://linear.app/docs/start-guide), [Teams](https://linear.app/docs/teams), [Workspaces](https://linear.app/docs/workspaces) | 2026-07-26 | Demonstration state is browser-local/resettable; navigation reflects actual teams; retired entities preserve history. | **Adopt／Adapt** | Guest is bounded and resettable; navigation reflects real duties; withdrawal/archive keeps audit and history. | Do not copy Linear UI or model a small Study Prefect team as a corporate org chart. |
| [OpenProject introduction](https://www.openproject.org/docs/getting-started/openproject-introduction/) | 2026-07-26 | The project lifecycle, task modules, user guide, admin guide, glossary, keyboard guidance and feedback routes are explicit. | **Adapt** | Weekly Pulse makes lifecycle position visible; help and reference pages provide progressive explanation and feedback paths. | Reject the broad project-management module set, pricing and deployment-choice complexity. |
| [Moodle Mt Orange School demo](https://docs.moodle.org/20/en/Mt_Orange_School_Demo) | 2026-07-26 | A demonstration environment can teach a real product through safe example data. | **Adapt cautiously** | Guest uses fictional Chinese names and the real page skeleton, while expensive/persistent capabilities remain restricted. | Reject shared mutable demo accounts and any path that can expose official data. |
| [NiceGUI repository](https://github.com/zauberzeug/nicegui) | 2026-07-26 | NiceGUI provides shared/individual pages, user/general persistence, custom routes and lifecycle/session state on FastAPI/Starlette/Uvicorn. | **Adopt within topology** | Continue one NiceGUI/Quasar runtime and central PageContext; keep Guest memory bounded to one controlled origin process. | Process memory is not multi-origin shared state; horizontal scaling is not claimed with SQLite/in-memory Guest sessions. |
| [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | 2026-07-26 | Least privilege, deny by default and permission validation on every request are baseline controls. | **Adopt** | Capability checks occur at route, callback and service boundaries; signed identity is revalidated for writes and downloads. | Hidden/disabled UI is never treated as authorization. |
| [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) | 2026-07-26 | Session state carries access and localisation; expiry, logout, cookie properties and lifecycle logging require explicit handling. | **Adopt／Adapt** | Guest preferences are session-bound; logout, expiry, revocation and restart clear bounded state idempotently. | Do not place official data or reusable authority in browser storage. |
| [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) | 2026-07-26 | Allowlist extensions, validate type/signature/content, limit size/name and authorize upload. | **Adopt** | Admin import validates extension, size, structure and content before preview/commit; Guest cannot upload. | Never trust filename or `Content-Type` alone; uploaded files do not become public assets. |
| [Staffjoy Suite](https://github.com/Staffjoy/suite) | 2026-07-26 | Historical workforce scheduling project with explicit service/configuration topology. | **Reject as implementation; retain one lesson** | Keep explicit configuration, health and operational dependencies. | The project is unmaintained and its multi-service architecture is disproportionate. |
| [Worklenz](https://github.com/Worklenz/worklenz) and [Rallly](https://github.com/lukevella/rallly) | 2026-07-26 | Maintained open-source products demonstrate focused workspaces and seeded/resettable development data. | **Observe only** | Use as corroboration for bounded demo fixtures and task-focused workspaces. | No code copying; their React/product/domain/licence choices do not define this NiceGUI system. |

## Information architecture contract

### Canonical page and state inventory

`nicegui_app/ui/page_catalog.py` is the navigation source of truth. Admin, Guest and Local Maintenance share the same workbench definitions for `/`, `/rosters`, `/prefects`, `/handover`, `/access-control`, `/settings`, `/platform`, `/system-architecture`, `/engineering`, `/getting-started`, `/guide` and `/devotional`; mode-specific adapters and capabilities change behavior, not the page skeleton. Actual handlers additionally retain the compatibility alias `/dashboard` and contextual child routes `/rosters/new`, `/rosters/{roster_week_id}`, `/adjustments`, `/rosters/{roster_week_id}/adjustments` and `/audit`. They stay out of primary navigation because they are entered from a parent workflow and must provide a visible return path.

The Cloudflare edge owns the public entrance, Admin start, Guest start／logout and encrypted `/view#…` viewer. The Viewer is a separate silent read-only state, not a Guest workbench page. Every page must account for loading, empty, restricted, error, conflict and recovery states; consequential Admin actions add confirmation and progress states, while Guest preserves the same explanation and spatial hierarchy with a server-enforced demo／restricted result.

### Public Product Entrance

Reading order is fixed: identity → purpose → Admin/Guest choice → weekly workflow → trust evidence → devotional opening → documentation routes. A returning authenticated user proceeds to the same Dashboard. The entrance contains no official roster query and no fake KPI claims.

### Unified Operations Workbench

The first working screen remains Daily Verse followed immediately by the next safe action. Weekly navigation follows the operator’s sequence, not the source-code structure. Related subpages expose a consistent parent link, stage marker and next action; browser Back remains functional. Tables and forms use solid high-contrast surfaces without background imagery.

### Trust & Engineering Hub

Trust is expressed as evidence, not adjectives. Each claim identifies an owning layer, current status, verification route and residual limit. Large explanatory sets use indexed lists or tables; cards are reserved for distinct decisions, not every paragraph.

### Documentation and Developer Portal

The portal offers two reading lanes:

- **Operate and hand over:** getting started, operator guide, handover and recovery.
- **Understand and maintain:** platform, architecture, engineering evidence, security and release procedures.

Search/filter, local table of contents, previous/next reading and copyable commands are useful patterns. A public API console, AI documentation assistant and key-management interface are out of scope.

## Responsive and motion decisions

- Desktop, tablet and phone share one information model; layout reorders rather than shrinking blindly.
- The dominant task remains first at every width. Tables may become day-grouped cards only when scan order is preserved.
- Controls remain geometrically stable. Icons may tell a short semantic story—open, refresh, complete, reveal—but containers do not drift, tilt or orbit.
- Motion uses the existing 90／180／260 ms contract, is interruptible, and becomes static under reduced motion, touch-only or forced-colour conditions.
- Waiting feedback is progressive rather than theatrical: contained press feedback is immediate; an inline indicator appears only after a genuine short delay; a persistent dialog is reserved for consequential work. A slow-state message explains that work is continuing and supplies a safe reference without inventing failure.
- Pointer-light may enrich the public entrance or a non-sensitive narrative surface. It is prohibited behind forms, tables, names, fairness records, warnings and PDFs.

## Stopping rule

A reference pattern is finished when it produces a measurable improvement in comprehension, workflow, evidence or safety and passes the owning contract. Additional cards, imagery, motion, corporate labels or documentation are not improvements by themselves. When a proposal adds a second visual dialect, a duplicate route or an unverifiable claim, reject it or replace an existing pattern rather than stacking it.
