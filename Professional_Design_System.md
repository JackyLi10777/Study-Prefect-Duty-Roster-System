# Professional Design System

**Project:** Sing Yin Study Prefect Duty Roster System  
**Version:** 1.2 — Quiet Precision institutional product contract
**Status:** Active design source of truth  
**Primary audience:** 負責日常操作的當任首席導學風紀、主要在完成後核對的顧問老師、未來維護者及實作代理人

**Canonical functional name:** `聖言中學導學風紀值班表生成系統`／`Sing Yin Study Prefect Duty Roster System`. `Service Weave／服事經緯` is the software product identity; shorter labels such as「值班表」只可用於已建立上下文的導航或頁面標題，不可成為另一個產品名稱。

---

## 1. Purpose

This document defines the visual and interaction standard for the local-first NiceGUI application. Its job is not to make a school system look fashionable. Its job is to help a 首席導學風紀 make a fair weekly decision calmly, understand its consequence, and hand the system to the next leader without depending on technical help.

The visual direction is inspired by the discipline behind contemporary iOS and Apple product experiences: clear hierarchy, precise type, considered materials, responsive feedback, and restraint. It is an original Sing Yin system. It must not copy Apple screens, assets, trademarks, liquid glass, or proprietary visual effects.

### Design thesis

> **A quiet school operations desk: one clear responsibility at a time, with enough evidence to act confidently.**

Interface copy is part of the operating model. Every sentence must help the reader choose an identity, understand a consequence, complete the current task, recover from failure, or verify evidence. Repeated trust claims, generic welcome language, self-congratulatory quality claims and labels that merely restate the page title are removed. Buttons use concrete actions; supporting copy states what happens next in concise Hong Kong written Chinese with complete English parity.

The signature interaction is **值週節奏 / Weekly Pulse**: the interface makes the current stage, the safe next action, and the durable result visible. It is not an animation for decoration; it is a consistent operational landmark across the dashboard, roster workspace, publication, adjustment, and handover.

### Jobs, audiences and journeys

| Audience／mode | Functional job | Emotional and social job | Required journey |
|---|---|---|---|
| Head Study Prefect／Admin | Prepare, review, publish, export, adjust and hand over a fair weekly roster | Feel in control under time pressure and be able to explain a decision responsibly | Access verification → Daily Verse → next safe weekly action → evidence／recovery → handover |
| Visitor／Guest | Understand the product and exercise the real workflow with fictional data | Explore confidently without fearing damage to school records | Public entrance → bounded Guest session → same workbench routes → clear DEMO state → expiry／reset |
| Teacher advisor／Viewer | Review an approved roster and understand the fairness and reliability model | Trust the process without being asked to operate it | Read-only share or public entrance → published roster／Trust & Engineering → no editing controls |
| Successor／operator | Learn the workflow, verify custody and take over safely | Feel supported rather than dependent on the previous operator | Getting Started → Operator Guide → Handover & Governance → supervised acceptance |
| Maintainer／developer | Locate architecture, update rules, verification and deployment procedures | Make changes without silently weakening policy or evidence | Documentation entry → architecture／security → update workflow → exact-source release evidence |

The social job is not to make the system look like a large company. It is to make fairness, stewardship and technical responsibility credible to the people who inherit or review the work.

### Four-zone information architecture

1. **Public Product Entrance** explains the product, audience, operating sequence, evidence and safe identity choices. It has no roster capability.
2. **Unified Operations Workbench** owns Getting Started, Weekly Operations, People & Fairness, Handover & Governance, Administration and contextual help. The weekly next action remains the dominant destination.
3. **Trust & Engineering Hub** combines architecture, security/privacy, fairness policy evidence, reliability/recovery and release/acceptance evidence. It is outside the routine weekly navigation lane even when reached through the shared shell.
4. **Documentation and Developer Portal** routes operators and maintainers to the correct guide, contribution workflow, deployment procedure and changelog without pretending the application exposes a public developer API.

Existing deep links remain canonical or receive explicit compatibility redirects. Admin and Guest use the same route definitions and components; only the verified `PageContext`, adapter, capability policy and data source differ.

### Considered alternatives

- **Site-wide soft Neumorphism:** rejected because low-contrast recesses, shadow-heavy hierarchy and press-like static cards weaken affordance and dark-mode reliability. Only the existing restrained token-backed elevation scale remains.
- **Separate marketing, Guest and Admin applications:** rejected because duplicated route trees, copy and components would drift and create a weaker security review boundary. One product shell with server-enforced adapters is easier to verify.
- **A single dense enterprise dashboard:** rejected because architecture, evidence and marketing content would compete with the operator's weekly task. Evidence receives dedicated zones and task-appropriate density.

### Author voice and handover narrative

The system has one human authorial voice: **李創杰，2026–2027 年度首席導學風紀**. Author introductions, motivation, design values, handover letters, project history, and co-creation conclusions must be written in his first person (`我` / `I`). They must not describe him at a distance as though an unrelated corporate narrator owns the project.

Codex is named as 李創杰's co-creator and technical colleague. A separately labelled “Codex 的結語” may use Codex's own first person, but it must not replace, merge with, or impersonate 李創杰's voice. Statements about the two-person team use `我與 Codex` / `Codex and I` when spoken by 李創杰.

Operational instructions, safety rules, current machine evidence, architecture contracts, and acceptance checklists remain direct, objective, or imperative. First-person authorship must make the handover more human without turning verifiable technical state into personal opinion. Traditional Chinese uses natural Hong Kong written language; the complete English version preserves the same speaker and meaning rather than reverting to third person.

### Feedback channel

The public project feedback address is `s10777@syss.edu.hk`, and the canonical source/documentation destination is `https://github.com/JackyLi10777/Study-Prefect-Duty-Roster-System`. They appear together as a restrained persistent sidebar resource group and as a fully explained panel in the Operator Guide and architecture/co-creation page. Both actions must be available in both languages and keyboard reachable; main-content actions remain at least 44px high. GitHub opens in a new tab with `noopener noreferrer`, while email uses the local mail client.

Feedback is distinct from technical evidence. Ordinary suggestions may use email directly; a failure should first preserve its OP/REQ reference. Copy asks for the reference and a short description only, never names, leave details, rosters, PDFs, databases, backups, screenshots, or complete logs.

### 2026.07 adaptive direction — Quiet Precision / 安靜精準

The next design level is not “more Apple-like”, “more corporate”, or “more decorated”. It is one coherent institutional product whose hierarchy, capability boundaries and evidence remain legible before any visual treatment is noticed. The research evidence, access dates and Adopt／Adapt／Reject decisions are recorded in [`docs/PRODUCT_RESEARCH_AND_IA_DECISIONS.md`](docs/PRODUCT_RESEARCH_AND_IA_DECISIONS.md); this document owns the resulting executable rules.

1. **Recognition before style:** the operator must recognise the current stage, primary action and consequence before noticing the visual treatment.
2. **One geometry grammar:** navigation, controls, cards, sheets and status markers share a small radius, spacing, icon and border vocabulary. Similar meaning produces similar shape.
3. **Quiet action colour:** primary actions use desaturated slate-blue; teal remains identity and verified/stable status. Colour never substitutes for text, icon or position.
4. **Solid material hierarchy:** page ground, quiet group, working surface and raised decision layer are separated by contrast, border and restrained shadow. Site-wide Neumorphism, persistent blur and transparent navigation are rejected.
5. **Motion has three speeds:** 90 ms press acknowledgement, 180 ms state change and 260 ms layer/entry transition. The **control container stays geometrically fixed** while a semantic icon may tell a short, obvious story—open, refresh, complete or reveal. Containers never drift, tilt or orbit; reduced motion is completely static.
6. **Controls form a dock:** page utilities are one compact solid cluster. The current navigation item uses text weight plus a position rail, not colour alone.
7. **Density follows consequence:** routine scanning stays compact; publication, restore, withdrawal and fairness consequences receive more space and plain-language explanation.
8. **Calm is not emptiness:** blank space separates decisions. Context imagery may enrich approved non-sensitive scenes, but never fills space that should communicate order.
9. **One product, four zones:** Public Product Entrance, Unified Operations Workbench, Trust & Engineering Hub and Documentation and Developer Portal share identity and tokens while retaining task-appropriate density.

This direction treats external design systems as evidence, not templates, and expresses the result through an original Sing Yin operational language.

### Current design mandate

This is the complete standing direction for future iterations. It replaces any tendency to make a generic dashboard, a literal Apple imitation, a HyperOS imitation, or a decoration-heavy template.

1. **Quiet operational luxury:** the normal application is a calm, orderly school work desk. Borrow the discipline of Muji-like material honesty—warm paper, linen, light timber, soft daylight, and generous empty space—without borrowing branding, product images, logos, or retail styling.
2. **Original digital precision:** use the useful principles of high-quality product interfaces—clear hierarchy, responsive feedback, coherent geometry, and readable system states—without copying Apple, Xiaomi, or any other company’s screens, assets, trade dress, or sounds.
3. **A separate sacred language for Scripture:** Daily Verse is a devotional pause rather than a work card. It must be visibly distinct, more contemplative, bilingual, dignified, and spiritually meaningful, while remaining compact enough that the weekly duty workflow begins immediately below it.
4. **One real weekly sequence:** Generate draft → review/publish and export → published-duty leave adjustment. Closely related tasks belong together; navigation must never make an operator hunt across unrelated pages.
5. **Purposeful imagery only:** use original, local, non-identifying imagery as low-opacity context for devotion, onboarding, handover, and empty states. Never place it behind forms, tables, student names, fairness data, PDFs, controls, or warnings. No text, people, school badge, watermark, or fake product UI inside generated imagery. Every enabled scene must have a deliberate light-mode and dark-mode companion asset, the same semantic slot and crop logic, independently tuned opacity/readability veils, and browser screenshots in both themes. Single-asset exceptions are not permitted. Animated GIF is prohibited throughout the product; approved animated artwork uses SVG for simple state motion or Lottie for more complex vector sequences under the media contract in section 8.
6. **Calm feedback, not theatre:** hover, press, one-time state changes, a short dialog settle, optional quiet success sound, honest progress phases, and low-volume page-context music are allowed. The local context player may make one low-volume autoplay attempt after a page becomes ready, with a browser-local default that the operator can turn off. It must expose playing／paused／browser-blocked／off states, an immediate pause/off control, and an explanation when browser media policy requires one manual start. No looping decorative animation, parallax, autoplay video, forced unclosable audio, fake loading percentage, bouncing icon, or motion that impedes reading.
7. **Accessibility and language are non-negotiable:** Traditional Chinese is primary, English is complete, names stay Chinese in every locale, keyboard focus is clear, touch targets are practical, reduced motion is honoured, and light/dark themes meet contrast requirements for text, icons, charts, tables, and system states.
   Appearance follows the operating-system colour preference by default; if the browser cannot resolve it during server rendering, the safe fallback is dark. The explicit control cycles system → dark → light, keeps a text alternative and never relies on the icon alone.
8. **Reliability is part of the experience:** a polished surface cannot disguise a failed save. UI changes must preserve policy ownership, persistent `history_weight`, publish-once ledger posting, leave-adjustment auditability, checksum-verified snapshots, managed restore, local-first privacy, and clear error/empty/confirmation states.
9. **Privacy before distribution:** no roster data is sent to generated imagery, media tools, analytics or an unauthorised client. The only distributed surface is one canonical workers.dev hostname. Public `/` has no application capability; a time-limited Guest session and an Access-verified Admin session enter the same NiceGUI routes through different HMAC-signed principals and adapters. Guest state contains only fixed fictional Chinese names, remains authoritative in bounded origin memory, and may place only the latest signed, session／workspace／tab-bound token in that tab's `sessionStorage`; it never enters official SQLite, backups, the fairness ledger, Viewer KV, AI, uploads, external delivery or content logs. After explicit confirmation, same-host `/view#…` links receive AES-GCM ciphertext for a minimum-field published-roster snapshot, keep no decryption key, expire or can be revoked. UI visibility is never the permission boundary.

### Design languages that intentionally differ

| Context | Design language | Must feel like | Must not become |
|---|---|---|---|
| Weekly roster work | Quiet operations desk: neutral surfaces, slate action, teal verified state, compact factual type | Calm, dependable, easy to scan | A KPI dashboard, a dense admin console, or a decorative template |
| Daily Verse | Sacred reading chamber: deep indigo, warm parchment/gold, serif reading type, measured space, low movement | A moment of reflection before service | A generic hero banner, a sermon slide, or a dark-themed work card |
| Public entrance and Guest | Editorial product narrative leading into the same workbench with a clearly bounded fictional-data adapter | Credible, understandable, safe to explore | A fake admin account, a marketing maze, or a copy of another platform site |
| Onboarding and handover | Gentle study archive: warm paper material, clear numbered action, reassuring recovery copy | A successor being calmly guided | A marketing landing page or tutorial carousel |
| Error, risk, and recovery | Plain spoken safety sheet: high contrast, direct action, visible consequence | Clear and accountable | An alarmist or vague system message |

### Original atmosphere assets

Original raster atmosphere artwork may be used only as a low-opacity contextual layer behind non-sensitive dashboard content. Current approved assets are:

- `nicegui_app/assets/atmosphere/weekly-pulse-light-v1.webp` — Weekly Pulse light-mode warm layered-paper context.
- `nicegui_app/assets/atmosphere/weekly-pulse-dark-v1.webp` — the same Weekly Pulse composition in its deep-indigo dark treatment.
- `nicegui_app/assets/atmosphere/devotional-sacred-light-v1.webp` — Daily Verse light-mode parchment-and-window context.
- `nicegui_app/assets/atmosphere/devotional-sacred-dark-v1.webp` — Daily Verse dark-mode evening-window context.
- `nicegui_app/assets/atmosphere/handover-archive-light-v1.webp` — Handover light-mode quiet archive context.
- `nicegui_app/assets/atmosphere/handover-archive-dark-v1.webp` — Handover dark-mode evening archive context.
- `nicegui_app/assets/atmosphere/platform-stewardship-light-v1.webp` — Platform & Team light-mode coordinated stewardship studio.
- `nicegui_app/assets/atmosphere/platform-stewardship-dark-v1.webp` — Same-composition evening companion for the Platform & Team hero.
- `nicegui_app/assets/atmosphere/onboarding-desk-light-v1.webp` — First-use light-mode prepared study desk context.
- `nicegui_app/assets/atmosphere/onboarding-desk-dark-v1.webp` — First-use dark-mode prepared study desk context.
- `nicegui_app/assets/atmosphere/sidebar-stewardship-light-v1.webp` — Light-mode, low-opacity local navigation material; the solid reading veil remains the contrast owner.
- `nicegui_app/assets/atmosphere/sidebar-stewardship-dark-v1.webp` — Dark-mode companion for local navigation material.
- `nicegui_app/assets/atmosphere/architecture-stewardship-light-v1.webp` — Light-mode header context for the non-sensitive system-architecture page.
- `nicegui_app/assets/atmosphere/architecture-stewardship-dark-v1.webp` — Dark-mode companion for the system-architecture page.
- `nicegui_app/assets/atmosphere/architecture-lifeline-light-v1.webp` — Light-mode six-station archival service-lifeline still life for the architecture showcase.
- `nicegui_app/assets/atmosphere/architecture-lifeline-dark-v1.webp` — Same-composition, same-crop evening companion for the service-lifeline still life.
- `nicegui_app/assets/atmosphere/guide-handbook-light-v1.webp` — Operator Guide light-mode handbook-and-desk context.
- `nicegui_app/assets/atmosphere/guide-handbook-dark-v1.webp` — Same-composition evening companion for the Operator Guide.
- `nicegui_app/assets/atmosphere/engineering-workbench-light-v1.webp` — Engineering & Quality light-mode verification workbench context.
- `nicegui_app/assets/atmosphere/engineering-workbench-dark-v1.webp` — Same-composition dark-mode verification workbench context.

They contain no people, student data, text, logo, or school crest. They must never replace a button icon, appear inside a roster table/PDF, or sit behind a form field. A solid or gradient readability layer, paired light/dark assets, matching pair dimensions, one shared crop/mask rule, and separately tuned theme opacity/readability veils are mandatory. An enabled contextual background may not use a single shared raster in both themes.

Enabled background art now follows a stricter pair contract. `ATMOSPHERE_THEME_PAIRS` in `nicegui_app/ui/theme.py` is the registry: sidebar, Weekly Pulse, Daily Verse, onboarding, handover, Operator Guide, Platform & Team, Engineering & Quality, architecture hero, architecture lifeline, and the shared empty-ready state each own exactly one semantic image slot and exactly two performance-sized files named `*-light-v1.webp` and `*-dark-v1.webp`. The component selector refers only to `--sy-image-<slot>`; `:root` supplies its light image and `.body--dark` supplies the corresponding dark image. This guarantees the same DOM position, crop rule, mask, and purpose in both themes. A dark image must be a theme companion, not an unrelated scene placed elsewhere.

Active atmosphere artwork is delivered as WebP and each file must remain below 250 KB unless a browser trace proves a justified exception. The current 22-file paired set totals about 1.83 MB. Browser identity marks also use purpose-sized derivatives: a 512×512 favicon and 640-pixel web crest prevent print masters from being decoded for small-screen presentation.

Legacy one-off atmosphere files are not retained as active or fallback backgrounds. If a new contextual background is approved, both theme files, the registry entry, the CSS variable, asset-existence test, and light/dark browser assertion must arrive in the same change.

The sidebar, Operator Guide, Platform & Team hero, Engineering & Quality hero, and architecture page are the only additional approved placement contexts in this phase. Their images sit behind a solid readability veil and never carry required information. They are **not** a reason to fill every blank area: useful breathing room remains part of a calm operating desk. Generated imagery is prohibited behind data tables, forms, warnings, names, fairness records, interactive controls, and PDFs（不可放在資料表、表單、警告或 PDF 後方）.

All future generated assets must be reviewed against this checklist before use: appropriate context; no implied real student; no readable text; no trademark or logo; local project copy exists; dark-mode opacity is specified; small-screen crop is safe; no required information depends on the image.

### Official school-crest assets

The school crest is an official identity asset, not generated atmosphere artwork. User-supplied PNG masters remain at project root; semantic delivery copies are retained under `nicegui_app/assets/brand/` and selected by context rather than by an ambiguous `logo.png` filename. The public entrance uses the transparent Service Weave `mark-light`／`mark-dark` pair and switches it from the same explicit theme state as the page; the fixed app-icon surface is reserved for favicon and operating-system contexts:

- `sing-yin-crest-favicon.png` — a 512×512 delivery copy for the browser favicon.
- `sing-yin-crest-navigation.png` — the purpose-sized 545×524 source for the 60×58 sidebar identity mark; using the supplied small master avoids repeated extreme downscaling.
- `sing-yin-crest-display-web.png` — a 640-pixel delivery copy for the architecture/co-creation seal.
- `sing-yin-crest-display-print.png` — the full 5983×5751 source reserved for PDF output.

The original alpha transparency is preserved; no JPEG conversion or automated background removal is allowed. Navigation and display crests use a transparent container in **both** appearances—no white tile, border or rectangular shadow may be added even on a white page. A restrained shape-aware drop shadow may follow the visible shield so the ribbon, red cross and dark-blue outline remain legible without creating a square. Keep the favicon, navigation, display, and print paths centralized in `nicegui_app/config.py`; future replacements must update these semantic files, retain Chinese characters and English school name, and pass browser and PDF verification at their actual rendered sizes.

### Creator identity media

`nicegui_app/assets/brand/li-chuangjie-avatar.jpg` and `nicegui_app/assets/brand/li-chuangjie-banner.png` are user-supplied creator identity content—not generated atmosphere or reusable background art. They may appear only in the `/platform` co-creation conclusion beside semantic text naming `李創杰 · LI Chuangjie, Jacky`. The canonical social destination is centralized as `INSTAGRAM_PROFILE_URL` in `nicegui_app/contact.py`; it opens in a new tab with `noopener noreferrer`.

Keep the supplied bytes and deliberate crop, provide bilingual alternative text and intrinsic dimensions, lazy-load/decode the media, and verify the containing surface, border and link contrast independently in light and dark mode. Essential identity, role and destination remain semantic HTML, so neither the Ichthys artwork nor the Greek banner text is the only source of meaning. Because these are foreground identity media rather than atmosphere backgrounds, they do not require synthetic light/dark duplicates. Never place them behind or inside a roster, directory, form, warning, fairness record, PDF or operational action.

---

## 2. Confirmed state and decision brief

### Current state

The active NiceGUI application already has policy safeguards, bilingual support, light/dark mode, verified backups, print-ready PDFs, contextual hints and a three-stage weekly workflow. The adaptive shell shares one 900px navigation breakpoint, renders repeated mobile navigation after the page content in DOM order, stacks simultaneous global status banners and applies one dialog-action grammar. Appearance and interface sound update in place; a dirty-form guard protects the only preference which still requires a page reload—language. The theme has a sound foundation—neutral surfaces, teal identity, restrained slate primary actions, rounded controls and tested contrast—but its information architecture must continue converging on one composed product rather than a collection of useful pages.

The live public gateway currently identifies the deployed origin as rc20. The active repository has moved beyond that release line, so historical rc20 gate counts prove only that immutable candidate; they are not evidence for the present working tree. A new candidate must pass exact-source verification, controlled Windows deployment, matching Worker deployment and online rendered checks before this document or the interface may describe it as live. Supervised Head Study Prefect and teacher-advisor acceptance remains a separate open decision until recorded.

### Head Study Prefect moment

At the start of a busy week, the operator needs to read the daily verse, see what stage the roster is in, make one safe action, and leave with confidence that the result is fair and recoverable. They should never have to scan a dense control panel, guess which color is actionable, or open several pages merely to understand the system state.

### Priority and trade-off

This is an **L2 workflow and visual-system improvement**. It should improve confidence, legibility, and handover before adding novelty. A dramatic theme, permanent animation, decorative illustrations, or excessive teal would make the system feel less serious and date faster. The priority is a consistent hierarchy and a distinctive operational rhythm.

### Strategy and evidence

The executable owner is the versioned `design_system/tokens.v1.json` contract. It generates `nicegui_app/assets/css/sing-yin-tokens-v1.css`, supplies the Quasar fill bridge through `nicegui_app/ui/design_token_contract.py`, and generates `cloudflare/roster_viewer/design-tokens-v1.generated.json` for Worker drift validation. `nicegui_app/assets/css/sing-yin-theme-v1.css` remains the compatibility implementation layer for base, layout, component, page, motion and utility selectors; it must not redeclare managed tokens. `theme_markup.py` contains only same-origin preload／stylesheet links and loads the token layer before compatibility and mobile CSS. `nicegui_app/ui/page_routes/` plus `page_shared.py` own page hierarchy, while `nicegui_app/ui/i18n_catalog/` behind the stable `i18n.py` facade owns bilingual copy. Every implementation phase must preserve policy boundaries, keyboard access, light/dark contrast, and browser evidence in both modes and at mobile width.

---

## 3. Principles

| Principle | Meaning in this system | Test before accepting a change |
|---|---|---|
| One responsibility at a time | A page shows one primary action for the current roster state. | Can a new 首席導學風紀 name the next action within five seconds? |
| Evidence before emphasis | Colour, elevation, and motion indicate real status, not decoration. | Does every accent explain an action, state, risk, or result? |
| Calm confidence | Space, type, and rhythm reduce stress during weekly work. | Would it still feel calm after 20 minutes of roster checking? |
| Servant leadership | Fairness, explanation, and recovery are visible, not hidden behind admin language. | Can the operator explain why an action is safe and fair? |
| Bilingual parity | Traditional Chinese is primary; English is complete. Chinese names never change. | Does the same hierarchy survive in both languages? |
| Accessible by default | Contrast, focus, touch target, and reduced motion are part of the component. | Can the task be completed by keyboard and in dark mode? |

---

## 4. What to learn—and what not to copy

### Learn from mature Apple-like product design

- **Hierarchy before decoration:** one dominant title, one dominant action, quiet supporting information.
- **Continuous geometry:** related controls share radii, padding, icon scale, and alignment so the interface feels intentional.
- **Material honesty:** use solid, high-contrast surfaces; depth comes from subtle border and shadow changes, not fake glass.
- **Motion as feedback:** a transition confirms a state change or preserves spatial context; it never competes with roster data.
- **Typography as interface:** large, confident page titles; compact but readable operational copy; numerical data aligned for comparison.
- **Restraint:** premium quality is felt through small consistencies rather than many effects.

### Explicitly rejected

- Liquid glass, persistent blur, transparent navigation surfaces, or translucent cards.
- Apple logos, SF symbols copied as product branding, proprietary screenshots, or a literal iOS clone.
- AI-looking illustration buttons, emoji-led navigation, rainbow gradients, and decorative motion without a task purpose.
- Teal on every interactive element. Teal is Sing Yin identity and verified/settled status, not a substitute for hierarchy.
- Site-wide Neumorphism, flat-on-flat controls, glowing twin shadows or recessed fields that reduce contrast or obscure an affordance.
- Shadow inflation on inactive surfaces, nested raised cards and press styling on non-interactive content. Depth is earned by consequence and ownership, not granted to every rectangle.
- Generic Tailwind shadow utilities applied outside the token system. Every shadow in the interface originates from `design_system/tokens.v1.json`.

### Critical adoption of SaaS website patterns

The common claim that a systematic SaaS layout automatically creates a clearer or more premium product is **plausible only within a defined scope**. Most of those patterns were developed for acquisition websites with several audiences, plans, and conversion goals. This system is primarily a single-administrator school operations tool, with a small public entrance and fictional trial. A pattern is adopted only when it measurably improves understanding, task completion, error recovery, or policy correctness; resemblance to a large commercial website is not evidence of quality.

| Proposed pattern | Decision for this system | Adaptation and boundary | Evidence required |
|---|---|---|---|
| Explain the product within the first few seconds | **Adopt for the public entrance; reinterpret after identity selection** | The public root states purpose, one Guest experience action and one Admin login action. The shared Dashboard then starts with Daily Verse and the next safe weekly action—not a marketing proposition. | In an unprompted check, a new visitor can identify the system purpose and choose Guest or Admin within five seconds; an operator can name the next safe action within five seconds. |
| Compare plans with cards and tables | **Reject as a literal pattern** | There are no prices, subscriptions or product tiers. A compact Guest／Administrator capability comparison is allowed only when it prevents a permission misunderstanding; it must not resemble an upsell matrix. | A reviewer can explain who may view, try, edit and publish without seeing a pricing or upgrade metaphor. |
| Introduce complex features progressively | **Adopt with consequence visibility** | Present purpose／outcome first, then the relevant task group, then details. Progressive disclosure may hide supporting explanation, but never a required field, policy restriction, publication consequence, recovery dependency, or current error. | A first-time operator completes the weekly path without opening unrelated pages; every consequential confirmation states the result before the final action. |
| Treat login as a complete interactive flow | **Adopt strongly** | Loading, disabled, expired, denied, verified, signed-out and safe-return states need explicit bilingual feedback. Cloudflare Access owns credentials; the product must not invent a parallel password or registration experience. | Keyboard and phone checks cover every access state, including expired／invalid sessions, and always offer one safe next action without a redirect loop. |
| Redesign mobile rather than shrink desktop | **Adopt, without creating a second product** | Reorder the same semantic content around the phone task sequence. Desktop and phone retain one URL, session, localized view model, policy, persistence, audit and PDF contract. | At 320px and 390px, the primary action precedes secondary evidence, no required information is omitted, and there is no unintended horizontal overflow. |
| Use 404, expired-link and denial pages to prove consistency | **Adopt** | Unknown routes, revoked／expired shares, failed administrator verification, origin unavailability and recovery states use the same type, spacing, focus, bilingual copy and semantic-status grammar as the main product. | Each state has a specific cause at the appropriate disclosure level, one safe recovery action, visible keyboard focus, both themes and no raw exception or sensitive data. |
| Assign modules, colour, type and components clear responsibilities | **Adopt as a semantic contract, not a slogan** | Modules group one operator job; colour communicates state; typography sets reading order; components provide predictable feedback. Layout and copy still carry meaning when colour, imagery or motion is unavailable. | Component tests and browser evidence show consistent tokens, non-colour status cues, readable hierarchy, reduced-motion parity and repeated interaction behaviour. |
| Add more imagery, cards, corporate narrative and “show-off” evidence to feel premium | **Reject by default** | Decorative density can increase perceived complexity and compete with roster work. Architecture and platform evidence remain bounded, truthful and secondary; imagery is admitted only in the approved non-sensitive contexts when it improves orientation. | A proposed module must name the user decision it improves and pass a before／after comprehension or task-flow check; otherwise it is removed. |

**Decision rule:** adopt the smallest version of a pattern that resolves a demonstrated operator or visitor problem. Revise or remove it if browser evidence shows slower task completion, a missed consequence, increased navigation, permission confusion, information loss on mobile, or weaker contrast／focus. “Premium”, “enterprise” and “modern” are value judgements, not acceptance criteria.

### Reference-led prompt and component protocol

The project may study public component galleries and design agents, but they are discovery tools rather than a second design system. The observed ideas and their Sing Yin adaptations must remain separate:

| Reference | Observed strength | Adopted adaptation | Rejected default |
|---|---|---|---|
| ReactBits | Demonstrates motion and interaction variants as isolated components | Use it to ask whether one restrained state transition could clarify feedback; reimplement only with the existing NiceGUI／Quasar／local-GSAP grammar | React-only source imports, shaders, cursor spectacle, looping text, animated backgrounds or landing-page motion inside operational screens |
| SuperDesign | Uses a strong screen default followed by a small set of hard constraints and delta-based iteration | Every design task names the operator moment, affected route and source files, retained structure, three to six constraints, required states and browser evidence | Vague “premium dashboard” prompts, full-screen regeneration and repeated aesthetic rerolls |
| 21st.dev | Organises examples by component, screen and theme and supports side-by-side variants | Search by the actual component problem—table, empty state, dialog, stepper—then compare structure before visual style | Installing community React／Tailwind components into NiceGUI or mixing several contributors’ visual dialects |
| Linear design analysis | Uses scarce accent colour, a stable surface ladder, hairlines and predictable spacing | Keep one action colour, semantic status tones, solid surfaces and stable spacing; let real roster content lead | Near-black-only branding, proprietary type, marketing screenshots, aggressive negative tracking and dark-mode-only rules |

Reusable design prompt for this repository:

```text
Operator moment: [one real Head Study Prefect decision].
Route and owners: [NiceGUI route/component files]; keep policy, workflow, persistence and URLs unchanged.
Keep: [existing information order and components that already work].
Change: [one evidence-backed friction], using existing Professional_Design_System tokens and components.
Constraints: Traditional Chinese first and complete English; Chinese names unchanged; one primary action;
AA contrast, visible focus, 44px touch target, light/dark/mobile parity and reduced-motion parity.
States: populated, empty, loading, error, disabled/busy and recovery where the component can reach them.
Avoid: KPI-dashboard defaults, new decorative imagery, glass, looping motion, copied brand assets and a new runtime dependency.
Evidence: focused test plus isolated desktop-light, desktop-dark and phone browser checks with zero console/page errors.
```

Iterate with one delta at a time. A reference may suggest a question or layout relationship; it never overrides the current data model, operator path, accessibility gate or design tokens.

### Useful inheritance from the former Professional Teal reference

- Respectful spacing, low visual fatigue, semantic colour, light/dark parity, accessible focus, and a local-first professional tone.

### Deliberately changed from that reference

- The direction is no longer HyperOS. It is a more structured, Apple-inspired original system language.
- Primary action colour is a muted slate-blue; teal is deliberately restrained.
- No blanket card nesting, generic KPI tiles, or decorative depth.

---

## 5. Token system

### 5.0 Executable contract and maintenance rule

`design_system/tokens.v1.json` is the only file in which a managed colour, motion, atmosphere, semantic status, component-control or Quasar bridge value may be changed. Its fixed layer order is:

1. **Primitive:** durable raw colours and motion values without UI meaning.
2. **Semantic:** action, stable, attention, danger, neutral, text, surface, focus and atmosphere roles for each light／dark platform.
3. **Component:** button, control depth, status capsule, hover and veil values that depend on semantic roles.

The two checked-in generated artifacts serve different deployment boundaries:

- `nicegui_app/assets/css/sing-yin-tokens-v1.css` is the same-origin `@layer sy.tokens` stylesheet consumed directly by NiceGUI before the compatibility theme.
- `cloudflare/roster_viewer/design-tokens-v1.generated.json` is the machine contract for the zero-network Worker. The Worker remains self-contained rather than fetching JSON at runtime; validation compares its inline light, explicit-dark and automatic-dark declarations with this generated contract.

Run `python -X utf8 scripts/generate_design_system_tokens.py` after an intentional contract change, then run `python -X utf8 scripts/generate_design_system_tokens.py --check`. The check fails if a generated file is stale, the NiceGUI loader order changes, compatibility CSS silently redeclares a managed token, the Quasar bridge diverges, or any Worker theme differs. Generated files are committed but never hand-edited.

### 5.1 Colour roles

| Token | Light | Dark | Purpose |
|---|---:|---:|---|
| `stable-teal` | `#0F766E` | `#72D6C7` | School identity and verified, published, completed, or settled states only |
| `action-slate` | `#35647C` | `#9BC2D2` | Links, outlined actions, current step, guidance and interactive icons |
| `button-action` | `#35647C` | `#47758B` | Filled primary button with white text; never used merely for decoration |
| `action-slate-soft` | `#E8F0F3` | `#1A2B34` | Current-step grouping and quiet action context; never a text-only state |
| `attention-amber` | `#8A5A00` | `#F0C96A` | Draft, missing prerequisite, practice mode, partial success or review needed |
| `danger-red` | `#963C35` | `#D98F87` | Destructive, blocked or failed state only; a muted brick/coral pair avoids alarm-red glare |
| `neutral-control` | `#5F6368` | `#C5C7CA` | Pending, inactive, ordinary navigation and non-status icons |
| `ink` | `#1C1C1E` | `#F5F5F7` | Important text |
| `secondary-ink` | `#6E6E73` | `#AEAEB2` | Supporting copy and metadata |
| `ground` | `#F2F2F7` | `#0D1117` | Page background; dark mode uses near-black mineral ink rather than pure black |
| `surface` | `#FFFFFF` | `#1C1C1E` | Cards, sheets, dialogs, navigation |
| `surface-subtle` | `#E5E5EA` | `#2C2C2E` | Tables, quiet grouping, disabled treatment |
| `devotional-gold` | `#D3A930` | `#FFD60A` | Scripture only; never a general call to action |

Rules:

1. One screen has one blue primary action at most.
2. Teal may identify the application, a completed or verified state, and devotional anchors. It must not colour all buttons.
3. Warning and danger are semantic only. Never use them for visual variety.
4. Text meets WCAG AA contrast: 4.5:1 for normal text and 3:1 for large text or UI boundaries.
5. A light dark-mode accent must carry dark foreground text when used as a filled step marker. Destructive dark-mode fills follow the same `on-danger` rule; white is not assumed to contrast with every semantic colour.

#### Component colour grammar

The interface never assigns colours icon by icon. A component first declares its semantic tone, and its icon inherits that tone:

| Semantic tone | Components | Examples |
|---|---|---|
| `action` | Filled/outlined CTA, current workflow step, progress, operation hint | Generate, save, export, open current draft |
| `stable` | Status badge or evidence only | Published, verified backup, completed step |
| `attention` | Status badge or recovery surface only | Draft ready, missing backup, practice, partial success |
| `danger` | Destructive action or failed status | Archive, remove, invalid/unreadable evidence |

Status capsules are semantic evidence, not tinted decoration. In light mode they use dedicated high-contrast foreground tokens (`status-action`, `status-stable`, `status-attention`, `status-danger`, `status-neutral`) rather than inheriting the softer icon colour; dark mode uses the corresponding luminous role token. Every capsule keeps a border, readable label and at least 28px visual height, and colour is never its only status signal. NiceGUI badges must opt out of the framework's default colour class (`color=None`); otherwise `bg-primary` can override the semantic background even when the token declaration appears correct. Browser verification measures the real computed foreground and composited background for all five tones in both themes, with 4.5:1 as the release floor. Slider landmarks must be placed by their numeric position rather than equally spaced labels: the history-priority scale therefore places 0.8 at 0%, 1.0 at one sixth, and 2.0 at 100%.
| `neutral` | Pending state and ordinary utility | Waiting step, empty-state symbol, secondary navigation |

Equivalent actions keep one tone even when their content differs: the share-safe roster PDF and internal audit PDF are both export actions, so both use action slate. Status and action are not conflated: a draft badge is attention/action-context, while “open draft” remains an action control. Colour is always accompanied by text, icon, border, position or state wording.

Settings follows the same rule at section level. Interface audio, local music, and YouTube are peer configuration sections, so their top rule and heading icon all use action slate; YouTube becomes teal only where a badge explicitly says the connection is ready. Backup warnings and the entry into restore use attention amber. The final restore confirmation uses danger red because it replaces the active database, even though the workflow first creates a safety snapshot.

Full illustrated empty states are reserved for orientation moments where a new operator must understand how to begin, currently the roster workspace before the first week exists. The Dashboard already carries the Weekly Pulse atmosphere in its primary workbench, so its recent-history rail uses compact neutral guidance rather than repeating a second scene. Music libraries, unavailable backups, recovery routes, and repeated empty panels likewise remain image-free. This prevents one paired scene from repeating down a page and keeps warnings, forms, and recovery decisions visually unambiguous.

### 5.2 Typography

| Role | Chinese-first stack | Use |
|---|---|---|
| Display | `PingFang HK`, `Noto Sans TC`, `Microsoft JhengHei`, system UI | Page title and important operational heading |
| Reading | `PingFang HK`, `Noto Sans TC`, system UI | Instructions, table text, forms |
| Devotional | `Noto Serif TC`, `PMingLiU`, serif | Scripture only |
| Data | `SF Mono`, `Cascadia Code`, monospace | Version, checksum prefix, technical path only |

Type scale:

- Page title: 30–34px, weight 700–750, tight tracking.
- Section title: 20–22px, weight 700.
- Card title: 16–18px, weight 650–700.
- Body: 15px, line-height 1.6.
- Supporting copy: 13px, line-height 1.55.
- Never reduce essential operational text below 13px.

### 5.3 Spacing and shape

Use a 4px base with a disciplined rhythm: `4, 8, 12, 16, 24, 32, 48`.

- Page edges: 20px mobile; 32–48px desktop.
- Section gaps: 24px normal; 32px when the user changes task.
- Cards: 20px radius for work surfaces; 14px for internal grouped controls; 12px buttons and fields.
- Do not use a radius merely because an element is a rectangle. Tables retain clear grid structure and restrained rounding.

### 5.4 Elevation

| Level | Use | Treatment |
|---|---|---|
| 0 | Page ground and tables | Boundary and contrast only |
| 1 | Standard cards and grouped work | Fine border + soft short shadow from the existing component tokens |
| 2 | Current action / open popover | Slightly stronger existing shadow and semantic blue/teal state treatment |
| 3 | Confirmation dialog | Clear solid surface, stronger existing shadow and dimmed background |

Do not layer a card inside a card unless there is a real change of task or ownership. Inputs remain solid fields with visible boundaries; they are not made “recessed” through low-contrast shadows. All shadows must resolve from `design_system/tokens.v1.json`; the specification must never name tokens that do not exist in that contract.

### 5.5 Material and texture

Premium tactility comes from a controlled material stack, not from filling every blank area with illustration. The shared implementation is `nicegui_app/assets/css/sing-yin-material-v1.css`, backed by same-geometry light／dark pairs in `nicegui_app/assets/materials/`.

- **Paper fibre** belongs to the page ground, header, Weekly Pulse, Daily Verse, handover hero, engineering hero and bounded editorial／evidence cards. It uses locally served, repeating micro-texture plus a restrained inset edge so large surfaces stop reading as flat template rectangles.
- **Linen weave** belongs to structural identity surfaces such as the sidebar. It may enrich an existing paired atmosphere image but must not become a second illustration or reduce navigation contrast.
- Light and dark assets share dimensions, seed, fibre direction and crop logic; only tone, opacity and blend mode change. The switch therefore preserves one material identity rather than replacing the scene.
- Texture is non-semantic and pointer-transparent. Removing it must not remove hierarchy, state, focus, content or an affordance.
- Texture is prohibited behind forms, fields, tables, roster cards, prefect names, fairness records, warnings, recovery consequences, export controls and PDFs. Those surfaces remain solid and maximally legible.
- Mobile reduces material opacity and complexity. `prefers-reduced-transparency` receives a quieter fallback even though no glass or blur is used.
- A new material is a system change: add a paired asset, a named variable, approved placement selectors, both-theme browser evidence, a sensitive-surface exclusion test and this specification in the same revision.

### 5.6 Visual hierarchy framework

Visual hierarchy is the ladder that guides the operator's eye through a page before colour, motion, or decoration can compete. The framework defines five ranked layers; every page element belongs to exactly one layer. Rankings compound through size, weight, colour saturation, and elevation—in that fixed priority—never through a single channel alone.

| Layer | Rank | Role | Typography | Colour | Elevation |
|---|---|---|---|---|---|
| **Dominant** | 1 | Page-defining title or the single primary action | 30–34px, 700–750 weight, −0.5px tracking | `--sy-ink` (maximum contrast) | Ground or current-action elevation |
| **Heading** | 2 | Section title, card group label, decision label | 20–22px, 700 weight | `--sy-ink` | Raised surface header |
| **Body** | 3 | Instructions, table text, form labels, card body | 15px, 400 weight, 1.6 line-height | `--sy-ink` (body) / `--sy-muted` (metadata) | Ground or raised, without independent elevation |
| **Supporting** | 4 | Metadata, captions, timestamps, version numbers | 13px, 400 weight, 1.55 line-height | `--sy-muted` exclusively | No independent elevation |
| **Quiet** | 5 | Legal, secondary navigation footnotes, archival markers | 12–13px, 350–400 weight | `--sy-muted` at reduced opacity | No elevation; background-assimilated |

**Hierarchy rules:**

1. **One dominant per page.** A second bold element competing for the same rank diffuses attention. If the page has a primary action button, its title and the button share the dominant rank but serve complementary functions (orient vs. act).
2. **Proximity signals grouping.** Elements separated by 8px or less belong to the same conceptual unit. Sections separated by 24px signal a task boundary. The 32px gap indicates a complete change of decision context.
3. **Weight drops predictably.** Heading → Body → Supporting → Quiet. The ladder never skips a step (no 30px title next to 13px metadata without a 15px bridging line).
4. **Colour saturation follows rank.** Dominant and heading layers use full-contrast ink. Supporting and quiet layers reduce saturation by 25–40%. Decorative colour never compensates for a missing weight step.
5. **Elevation amplifies interaction, not decoration.** Only consequential interactive elements receive stronger depth. Static content stays at ground or raised level without press affordance.
6. **Empty space is a hierarchy signal.** The gap between the dominant layer and the first heading is the largest on the page (40–48px). The gap between a heading and its body is 8–12px. Consistent spacing ratios make the hierarchy predictable without reading every label.
7. **Mobile preserves the ladder, reorders the layout.** At phone width, the dominant layer stays first in reading order. Below 390px, heading weight may reduce from 700 to 650 to prevent line-wrapped titles from dominating. No layer is omitted; no new decorative element is introduced to fill reflowed space.

---

## 6. Layout system

### 6.1 Dashboard: Weekly Pulse

The dashboard is the product thesis. Its order is fixed:

```text
Daily verse (compact, dignified, immediately visible)

This week's roster desk
  Current stage / next primary action
  [Draft] → [Review & publish] → [Published-duty absence]

Recent roster history (quiet, secondary)
```

- The daily verse comes first but remains compact; its reflection is progressively disclosed.
- The current step carries blue emphasis. Completed steps use teal confirmation. Future steps are neutral.
- The primary button opens the relevant working page directly.
- Recent history stays subordinate. On wide desktop it occupies one compact right-hand review rail beside the workbench; on narrower screens it follows the workbench in the same DOM order. It uses one containing surface with divided list rows—not a wall of equal cards—and must not compete with the current action.

### 6.1.1 Daily Verse: sacred reading component

The Daily Verse is a distinct component, not a recoloured dashboard card.

- **Structure:** small book mark; bilingual devotional label; Scripture in serif reading type; reference; quiet refresh control; one progressively disclosed reflection. The main dashboard version remains compact; the `/devotional` page may use the fuller reading chamber.
- **Canonical translations:** every maintained direct Scripture quotation uses Traditional Chinese RCUV 2010（神版）and English NKJV, with the versions named explicitly near the reading. Content comes from `data/devotional/daily-verses.seed.json`; release validation fails when either translation metadata, Scripture text, or exact-verification state is absent or wrong. A service-principle paraphrase must be labelled as a principle and must not masquerade as a verbatim verse.
- **Materials:** deep indigo surface, warm parchment text, restrained gold rule, and a local right-weighted contextual image. In light mode it uses `devotional-sacred-light-v1.webp`; dark mode uses `devotional-sacred-dark-v1.webp`.
- **Reading protection:** a solid left-to-right veil protects text; the image is never the sole contrast mechanism. Scripture may never sit on a busy crop, an animated layer, or a translucent glass panel.
- **Motion:** no automatic movement. Hover may deepen elevation only; verse refresh is an explicit action and changes content without an ornamental page transition.
- **Separation:** blue remains a work-action colour below. The Daily Verse uses gold and parchment only within its own surface, so it is recognisably sacred without turning the application into a themed template.
- **Direction:** the operator may choose `Follow appearance`, `Clear guidance`, or `Quiet comfort`. Follow appearance initially maps light mode to service, justice, wisdom, and witness; dark mode maps to prayer, care, perseverance, faithfulness, and spiritual formation. This is a recommendation rather than an emotional stereotype: the explicit operator choice persists, refresh remains manual, and the selected direction filters only already-polished bilingual entries.
- **Full-page journey:** `/devotional` keeps the Scripture dominant, then offers three bounded companion steps—reflect, pray and carry the reading into today’s service. These are reading aids, not new policy or generated theology, and the weekly-work return remains obvious.

### 6.1.2 Music atmosphere profiles

Music is page-context-aware and makes one controlled autoplay attempt at the 50% browser-local default after a page becomes ready. The operator can pause it or disable browser-local autoplay from the current page or Settings; that preference persists until changed. Browser media policy remains authoritative, so a blocked attempt becomes a clear manual-play state rather than repeated retries. The implemented system has one `Follow appearance` preference plus two independently selectable profiles:

- **Bright focus:** gentle forward movement, clarity, hope, service, and the beginning of work; suitable for light-mode default recommendation.
- **Quiet reflection:** slower pacing, reassurance, patience, prayer, and handover; suitable for dark-mode default recommendation without implying sadness.

Appearance selects only the recommendation when the operator has not chosen a profile. A saved profile overrides appearance until reset. Both profiles contain several page-specific tracks, support sequential/shuffle playback, and remain subordinate to page context, saved volume and the visible pause/off control. Vocal and instrumental editions use separate stable arrangement codes and visible bilingual labels; byte-identical duplicate files do not become repeated catalogue entries. A bounded link import may add authorised audio to `music/youtube-imports/`, but it remains an explicit Settings action with an honest waiting state and never runs on page load or appearance change. YouTube embeds remain separately user-started; local context autoplay must not silently initiate third-party playback.

The public login entrance has a narrower welcome-music contract. It uses five allowlisted **instrumental** tracks for each appearance profile, gives browsers without a saved preference the shared default of **50%**, and exposes play／pause, next-track and volume controls beside the identity choices. Every explicitly stored level remains authoritative, including a previously selected 25%; a revision marker must never reinterpret a saved number as an old default. Every fresh entrance attempts audible playback. If browser media policy blocks it, the interface shows a browser-blocked state and retries once after the first eligible page interaction; it never loops, opens a modal or overrides an explicit pause during that visit. Light mode begins with `Morning Has Broken`; dark mode begins with `Ubi caritas`, while subsequent tracks rotate without using vocal recordings. Changing appearance switches the paired playlist but never changes authentication, Guest state or roster data. Only exact stable track IDs are available through `/welcome-audio/<id>`; filenames, arbitrary origin paths and the music directory are not browser inputs. The encrypted `/view#…` roster surface remains silent.

### 6.2 Roster workspace

The roster page follows a **prepare → decide → confirm** hierarchy:

1. State and week context.
2. Pre-generation leave and vacancy evidence.
3. Generate draft or choose a published adjustment.
4. Draft table as the inspection artifact.
5. Publication/adjustment confirmation at the moment of consequence.

The Assist. in charge mode is a compact policy decision inside the prepare stage, not a decorative filter. Its selector maps bilingual labels onto the stable codes `legacy_fixed_weekday` and `flexible_weekly`; translated text must never enter the rule engine or database as a key. New weeks visibly default to fixed-weekday mode, while an existing week always opens with its persisted mode. The helper copy states the operational consequence before generation: legacy mode preserves each AHP's weekday ownership while the active directory and availability remain unchanged; recorded leave uses a qualified week-local substitute without rewriting that ownership, and an unresolved vacancy stops generation. Flexible mode uses the week as a deterministic variation key, keeps persistent fairness history as the primary cost, and avoids each AHP's previous-week weekday when availability and feasibility permit. Only Assistant Head Study Prefects are eligible for `Assist. in charge`. In the prefect dialog, the optional fixed Assist weekday appears only for an AHP, only affects legacy mode and must be one of that prefect's selected available days. The availability helper states that selected days are eligible and unchecked days are unavailable; neither Assist. mode nor room scheduling may override that boundary.

The roster grid is an operational document, not a dashboard chart. Preserve the row/weekday/name structure, give headers a stable surface, and allow names to dominate cells. Avoid visual effects inside the table that reduce print or scan clarity. At phone width, render the same roster data as day-grouped duty cards: each card keeps the post, time, Chinese name, status, and workload together. Do not force a person to horizontally scroll to discover a name or use a different data source for the mobile presentation.

### 6.3 Directory, fairness, and settings

- **Directory:** show the active people list first; editing and archive actions are clearly secondary to identity accuracy. On a phone, render the same localized directory data as individual identity cards—Chinese name, form/class, role, availability, workload, and duty count—rather than clipping a seven-column table.
- **Import:** use a staged form—template or file, worksheet, field mapping, local validation, data preview, explicit import—rather than one large ambiguous text area. Keep the optional heading-suggestion service inside a quiet secondary card; manual mapping remains the complete path, and a suggestion may populate controls but never skip human review or become a write action.
- **Fairness:** position the explanation before the numbers. Data should answer “why”, not merely display totals. The period report stays in this same tab because the operator uses it to explain the ledger, avoiding an unnecessary page change.
- **Period report:** start with whole-week range controls and a read-only state marker; then show coverage／ledger metrics, a plain-language executive summary, the historical distribution, and named participation. Downloads come only after the on-screen preview. “Scheduled hours” always carries the visible qualifier “not attendance evidence”, and JSON always carries “report evidence, not a restore backup”.
- **Settings:** separate routine status from high-consequence recovery. Restore and export backup packages must remain confirmation-gated.

Import forms, report metrics, contribution tables, trend data and download notices are sensitive operational surfaces. They remain image-free in both themes. Hierarchy comes from spacing, type, neutral surfaces and semantic status tone—not illustration, background texture, pointer light or decorative motion.

### 6.3.1 Canonical-site access control and five security states

The canonical workers.dev hostname is one branded system with five clearly distinguished application states, not five websites or an account dashboard:

- **Public entrance `/` · Choose the safe next step:** without a verified application session, the editorial entrance contains no roster data or write capability. It explains purpose, the Guest experience, the separate published-roster link and the one administrator action.
- **Guest · Experience the real product safely:** after **Guest experience**, the Worker creates a bounded session and the origin renders the same NiceGUI routes, navigation and components through a fictional-memory adapter. A persistent `DEMO` identity, remaining-session consequence and restriction states make the boundary clear without pretending that disabled Admin functions are available.
- **Published roster `/view#…` · View one issued snapshot:** a calm, factual roster surface for locally decrypted ciphertext. It must look read-only, show expiry／latest-link guidance and never imply that the Viewer token opens editing.
- **Administrator · Operate after verification:** reached through one unmistakable solid **Admin login** action on the entrance. Cloudflare Access owns account sign-in and MFA; successful verification returns to the same `/` and resolves the official NiceGUI workflow through VPC. A persistent **Log out** action explains that it returns the browser to the public entrance.
- **Local maintenance · Recover under host control:** loopback／approved maintenance access keeps the same operational product but exposes no new policy or data capability beyond the verified local principal.

`/guest` and `/try` are compatibility redirects, not separate products. Guest is a real NiceGUI application mode with deny-by-default capabilities, a bounded fictional workspace and the same navigation grammar as Admin. The browser stores only a signed snapshot token in `sessionStorage`; a live connection nonce plus SID／workspace／tab／revision binding is required for restore. Duplicated tabs receive new workspaces, while copied, tampered, expired, stale or old-boot tokens fall back to the safe fixture. The interface must show these consequences without implying that colour or a disabled button is the security boundary.

The platform-story sequence may learn from the information architecture of mature product and documentation sites—clear value statement, capability groups, one guided starting action, trust explanation, FAQ and resource footer—without copying their screen composition, text, visual assets or brand language. [Claude Platform](https://claude.com/platform/api) and [Claude Platform Docs](https://platform.claude.com/docs) are research references for hierarchy only, not templates.

Every web page uses the shared, low-interference authorship footer `Copyright © 2026 LI Chuangjie` beside the servant-leadership principle. The public entrance／viewer and the NiceGUI workbench must render the same wording, preserve contrast in both themes and stack cleanly on narrow screens. This website authorship mark is not forced into the clean roster PDF; PDF footer content remains an explicit export option so group-sharing layout and operator intent stay unchanged.

On a wide screen, the root uses a 58/42 editorial composition: the larger story column explains purpose, the three-stage weekly sequence and a compact sacred reading; the smaller access column explains the current permission state, the one next action and three bounded trust facts. It is not a marketing carousel. Below 700 px the same semantic blocks stack in reading order, and 320 px remains the minimum browser evidence width without horizontal overflow. The root offers **system / light / dark** appearance states; forced-colour mode retains native borders and text, and keyboard users receive a skip link plus visible focus.

The public entrance uses one original paired editorial scene: `cloudflare/roster_viewer/public/assets/entrance-operations-light-v1.webp` and `entrance-operations-dark-v1.webp`. Both are the same 1760×941 composition: an unlabelled duty ledger, pen, folders, three paper markers, a fine teal line and a restrained brass detail. The light scene suggests a prepared morning; the dark scene changes only illumination and material tonality. It contains no people, student data, writing, logo, crest, screen, fake interface or watermark. A solid theme-coloured veil protects all copy, and the two files occupy the same DOM slot, crop and semantic purpose. The imagery is decorative; the weekly sequence remains real text and never depends on the picture.

The root devotional is a compact invitation to pause before work, not an advertisement or an auto-rotating banner. It uses a small local selection contract-tested against the canonical devotional corpus, displays RCUV 2010（神版）and NKJV together with a short reflection, chooses a Hong Kong date-stable initial item, and changes only when the visitor activates **Show another verse**. It does not autoplay, fetch Scripture from an external API, infer a different translation from browser language, or create a dependency on NiceGUI／SQLite／KV.

The access panel may include one quiet **Share this site** secondary action. It always shares the canonical root URL and must state that no roster, fragment key or edit permission is included. It is visually and semantically separate from the post-publication `/view#…` roster-link workflow, so the operator cannot mistake “share the product entrance” for “share this week’s duty roster”.

The interface must not ask the operator to remember `/auth/*`, localhost, WARP, VPC, or a second administrator URL. The Access session consequence—eight hours maximum, log out on a shared device—uses plain bilingual copy. Password reset, password strength, hash, and local account controls do not appear because the application has no custom password database. The Access policy and Worker configuration share a bounded exact-email administrator allowlist; the UI never turns an unverified email, query string, cookie flag or Viewer token into edit permission.

Active viewing links remain text-first, image-free records. Week, expiry, and a short link identifier form the scan order; revoke is a danger action with an explicit consequence and the approximate one-minute edge-propagation note. A link receipt is persistent until the operator closes it, uses a readonly text field, and places **Copy link** above secondary dismissal. It must say that the key is displayed once and that the complete link grants viewing until expiry or revocation.

The `/view#…` Worker viewer remains a quiet document surface, not a miniature dashboard or a continuation of the editorial root. It uses Traditional Chinese first, complete English context, Chinese names, system fonts, a restrained teal published marker, and a high-contrast roster matrix. It supports light/dark preference, phone horizontal table access with a visible bilingual swipe instruction associated through `aria-describedby`, A4-landscape print, reduced motion, and honest loading/error states. It contains no atmosphere image, school-data background, animation showcase, music, third-party font, analytics, advertising, or edit affordance. Admin login is an identity transition, not a suggestion that the visible roster itself is editable. Protected-operation explanations use neutral trust surfaces; gold remains reserved for devotional reading.

Root presentation motion is restricted to one initial 380–440 ms transform/opacity settle, a small press/arrow response on the real access actions, a brief manual verse replacement, and a fine-pointer-only image-depth response bounded to 8 px horizontally／6 px vertically. The depth response is tied directly to pointer position, resets on leave, never scroll-parallaxes, and is removed under `prefers-reduced-motion`. Nothing loops, floats continuously or auto-advances. All content is immediately visible and state changes remain understandable without movement. These visual rules do not alter Access destinations, signed-principal verification, the VPC proxy, Viewer encryption, or the Guest/Admin capability boundary.

Viewer success is measured by one question: can a recipient open the complete link and understand the current published duty in one scan? Decorative richness must never compete with names, dates, posts, duty times, expiry, or the read-only consequence.

### 6.4 Responsive rule

- Desktop: content has a readable max width, not a full-width administrative spreadsheet.
- Tablet: at `640–900px`, operational forms retain one clear column while evidence summaries, downloads, developer commands and reference grids may use two readable columns. At `901–1180px`, a landscape touch tablet keeps the compact desktop navigation shell but collapses compressed operation／document layouts and limits evidence or download groups to two columns.
- Mobile: primary action remains before secondary information; grids become ordered vertical lists. The roster uses day-grouped cards, not a horizontally clipped table, so every Chinese name, duty time, status, and workload is readable in one card.

Phone layout is a deliberate arrangement of the same product, not a compressed desktop canvas and not a second website. Desktop and phone share one canonical URL, login/session, NiceGUI routes, localized view models, SQLite data, workflow and policy engine. Never branch policy, permissions, persistence, audit or PDF behaviour by user agent.

- `<= 900px` is the adaptive navigation shell; `> 900px` keeps the desktop drawer and utility row. Tighter content rules may still activate at 600px, but Quasar's drawer breakpoint, CSS navigation swap and bottom-nav visibility must never disagree.
- The phone top bar stays on one line and contains only page identity plus the optional page-music control. Appearance, language, sound, logout and secondary destinations move to the **More** navigation drawer instead of wrapping the header.
- A persistent four-item bottom navigation exposes **Dashboard / Rosters / Prefects / More**. It respects `env(safe-area-inset-bottom)`, keeps practical targets at least 44px, identifies the current destination without colour alone, and adds enough content padding that the final control is never hidden underneath it.
- **More** opens the same semantic navigation drawer used by the shared shell. It must remain vertically scrollable at 256px and 320px, support keyboard and screen-reader navigation, dismiss through the platform-standard drawer interaction, and keep destructive or identity-changing actions clearly labelled. When opened, **More** sets `aria-expanded=true`, moves focus to its first available control and contains Tab／Shift+Tab navigation; Escape or backdrop dismissal closes it, restores focus to **More** and returns `aria-expanded=false`.
- A secondary route keeps **More** visually associated with the current section, but the menu trigger itself must not claim `aria-current=page`; the exact current destination inside the drawer owns that semantic state. Shared-route navigation transfers focus once to `main#main-content`, while reloads and direct visits do not steal focus.
- The document has no fixed 320px minimum width. At narrow CSS viewports created by 200% zoom, the shared canvas reflows down to 256px without document-level horizontal scrolling; only an explicitly labelled data region may opt into local scrolling.
- Phone keyboards are treated as a visual-viewport change. While a keyboard materially reduces the viewport, the fixed bottom bar yields, focused fields scroll into a safe central region, and listeners are disposed on route replacement. This adaptation never changes validation, data, or submission semantics.
- A 640–900px tablet is not a stretched phone: operational forms retain one clear column, while evidence and developer-reference grids may use two readable columns. The candidate device matrix uses both 768×1024 and 820×1180 portrait tablets to prove that adaptive composition; a 1024×768 landscape tablet proves the compact desktop shell with one-column operational decisions and two-column supporting grids; 1440×1024 proves the full desktop shell and reading measure coexist without inheriting tablet compression. Workflow steps stack at the narrowest zoomed-phone widths, use a contained sequence on phones and return to a two-column overview on tablets.
- Dense tables use cards, row detail or another scan-safe phone representation generated from the same localized display model. A mobile card may reorder information, but it may not omit names, status, workload, reasons or actions needed for the same decision.
- Landscape phone layout is a compact phone composition, not an automatic return to the desktop sidebar. Hover is never required; form actions stack in consequence order and touch targets remain separated.

### 6.5 Platform story and architecture evidence

Brand context and technical evidence use two connected pages instead of one oversized showcase.

**Platform & Team (`/platform`)**

1. Begin with the human service thesis and a same-composition light/dark stewardship image; the image remains decorative behind a solid readability veil.
2. Show only anonymous live evidence: active-prefect count, roster-week count, verified-backup state, and display-safe release checks. Never show names, classes, leave, roster content, audit payload, database paths, or backup paths.
3. Preserve official school roles and pair them with explanatory responsibility titles. Weekly Operations, Fairness Assurance, Service Experience, and Systems Continuity are capability lanes, not claims of extra departments or headcount.
4. Organise features around four operator outcomes with direct routes into the real workspaces. Copy begins with the job and expected result, not technology.
5. Connect service, fairness, clarity, responsibility, and continuity to concrete system behaviour. End with resources, feedback, and the two-person co-creation narrative.
6. If the read-only snapshot fails, keep the complete static story visible and show a neutral bilingual support reference; never render the exception.

**System Architecture & Trust (`/system-architecture`)**

1. State local-first, verifiable, handover-ready operation and link to Platform & Team for organisation context.
2. Show the real six-stage week—prepare, draft, publish, export, adjust, hand over—as an ordered semantic list. Desktop uses a connected horizontal rail; tablet uses a readable three-column map; mobile uses one vertical line without horizontal scrolling.
3. Keep the paired architecture-lifeline image decorative; five ownership cards explain interface, policy/core, workflow, persistence/recovery, and handover.
4. Four evidence cards name durable proof for policy isolation, publish-once fairness, verified recovery, and privacy boundaries. FAQ answers identify a safe next action.
5. Do not duplicate the organisation chart, capability map, solution portfolio, or co-creation close on this page.

**Engineering & Quality (`/engineering`)**

1. Treat the page as an engineering evidence centre, not a KPI dashboard or technology-logo wall.
2. Numbers must be release-controlled structural evidence: automated tests, verification gates, owning layers, and complete locales. Usage, adoption, uptime, security grades, or business outcomes may not be invented.
3. Present the five-layer blueprint and the current report-backed release gates as semantic ordered lists. Gate totals and passed counts must come from non-stale release evidence; connectors are CSS decoration only and reading order remains complete without them.
4. Use neutral surfaces, monospaced evidence numbers, slate action colour, and teal only for verified or durable outcomes. Dark mode receives separately checked text, border, and state contrast.
5. Keep the page read-only. It may consume display-safe release evidence but never workflow, roster, leave, fairness, backup path, or audit payloads.
6. On mobile, facts, blueprint layers, gates, capabilities, and evolution stages become one ordered vertical sequence without horizontal scrolling.

Enterprise references inform information order, not visual imitation. Platform, solutions, trust, resources, and company/team narratives must be translated into the Sing Yin context with original geometry and copy. A generated narrative image may support the non-sensitive operating-model story only when a same-composition light/dark pair is present; organisational meaning must remain in semantic HTML, never inside image text or a fake diagram.

### 6.6 Reference and documentation information architecture

The website already owns the necessary reference routes; professionalism comes from connecting them, not multiplying top-level pages. Two reading lanes are canonical:

- **Operator lane:** Getting Started → Operator Guide → Handover.
- **Trust lane:** Platform & Team → System Architecture & Trust → Engineering & Quality.

The information architecture may learn from the grouped navigation, page-local contents, cause／solution tables, curated update history and previous／next continuity used by mature documentation systems such as [DeepSeek API Docs](https://api-docs.deepseek.com/zh-cn/), its [error reference](https://api-docs.deepseek.com/zh-cn/quick_start/error_codes/) and [update history](https://api-docs.deepseek.com/zh-cn/updates/). The implementation remains original and follows these constraints:

1. Do not create an API-style sidebar, pricing page, model catalogue, developer-console imitation, or a second operator manual merely to resemble a software platform.
2. Getting Started is the compact index. It answers three real situations: begin weekly work, recover from uncertainty, or understand trust and fairness.
3. Operator Guide groups instructions by decision stage and includes a bilingual **what you see／what it means／safe next action** reference. It uses existing workflow meanings and support references; it must not invent public error codes.
4. Page-local contents links wrap on mobile and remain in normal document flow. They are never a second sticky sidebar competing with weekly navigation.
5. Previous／next links stay within one reading lane. An operator is never sent unexpectedly from a recovery instruction into a technical showcase.
6. Engineering updates are curated operator-visible milestones backed by release evidence. Internal styling rounds, unverified counts, and marketing-style release claims stay out of the interface.
7. Reference navigation chrome, page-local contents, pagers and troubleshooting matrices are image-free. Their hierarchy comes from typography, spacing, semantic links, structured rows, focus states and concise bilingual copy. The `/platform` co-creation block may show foreground creator identity media only under the separate Creator identity media contract; it is never a reference background or a carrier of workflow meaning.

---

## 7. Components and interaction patterns

### Navigation

- Group routine pages by real work in this order: Getting Started, Weekly Operations, People & Fairness, Handover & Governance, Administration and Contextual Help. Platform story, engineering evidence and developer architecture remain available through a separate Trust & Documentation portal outside the routine task groups.
- Active navigation has a blue selection field and remains visible in both themes.
- Icons are one consistent Material outline family, supporting—not replacing—text.
- Limit primary navigation to the current operating map; archive old routes only as redirects for bookmarks.
- Desktop keeps the grouped sidebar and full utility controls. Phone replaces that shell with the one-line top bar and four-item bottom navigation; this is an alternate presentation of the same routes, never a parallel `/mobile` tree.
- **Dashboard**, **Rosters** and **Prefects** are the three routine phone destinations. **More** owns Handover, Settings, Platform & Team, Engineering & Quality, System Architecture & Trust, Getting Started, Operator Guide, Daily Verse and utility controls in a calm grouped bottom sheet.
- A route opened from **More** remains visibly identified and keeps **More** as its navigation context. **More** is a menu trigger, not the page itself: it does not receive `aria-current`; the current drawer item does. Browser back, deep links and refreshed pages must preserve the same canonical route rather than redirect through a mobile home page.
- The fixed bottom navigation is visually persistent but appears after `<main>` in DOM order. Keyboard and assistive-technology reading order therefore encounters the unique page content before repeated navigation.
- A shared-route action records navigation intent before leaving. After the new route renders, focus moves to `main#main-content` without a second scroll jump so keyboard and screen-reader users receive fresh page context; direct visits, ordinary reloads and fragment navigation keep their own focus behavior.
- Appearance and interface-sound controls update every desktop／mobile instance in place without reloading or discarding form state; enabling sound gives one brief preview. Language remains a full translated-page reload, so trusted edits inside `<main>` must trigger a bilingual leave confirmation before that reload.

### Buttons

| Kind | Use | Visual rule |
|---|---|---|
| Primary | The one next consequential action | Low-saturation slate-blue fill with white text, existing token-backed control shadow, clear verb and minimum 44px target. |
| Secondary | A valid alternative or review path | Warm／dark neutral surface, semantic outline and the shared outline shadow. Same geometry as Primary. |
| Tertiary | Navigation or low-risk discovery | Quiet surface response without independent elevation. Icon only when it clarifies meaning. |
| Attention | A safe recovery or unresolved prerequisite | Amber outline／surface; never decorative variety and never a substitute for error copy. |
| Destructive | Archive／remove／restore-overwrite action | Muted-red danger treatment with a persistent label and explicit consequence confirmation. |

**Button interaction contract (all families):**

1. Geometry and label width remain stable in every state; hover cannot move surrounding content.
2. Fine-pointer hover may deepen the existing token-backed contrast or shadow. Coarse pointers receive the same meaning through press and focus states.
3. Press acknowledges input within 90ms using a contained change of colour, shadow or at most 1px travel. A narrative icon may change shape, but the button container must not drift, tilt or rotate.
4. Disabled and busy states expose real `aria-disabled`／`aria-busy` semantics and prevent duplicate activation; visual treatment alone is insufficient.
5. Dark mode uses the paired semantic tokens. It does not simulate a separate light source or add glowing white edges.
6. Reduced motion presents the same state changes without transforms or animated icon sequences.

### Shared component state matrix

| State | Required signal | Reliability／accessibility contract |
|---|---|---|
| Rest／selected | Stable label, boundary and current-state marker where relevant | Selection uses text, geometry or `aria-current`／checked state as well as colour. |
| Hover／focus-visible／pressed | Bounded token-backed feedback; focus ring remains visually dominant | No layout shift, no host rotation and no hover-only meaning. |
| Loading／pending | Real phase label; skeleton only when content shape and a genuine delay are known | Set busy state, prevent duplicate activation and retain the initiating context. |
| Success／warning／error | Semantic icon, plain-language result and next safe action | Do not expose raw exceptions; success is shown only after the owning transaction finishes. |
| Disabled／permission-denied | Persistent label plus why and what remains possible | The server and service layer must still deny a direct request. |
| Empty | Explain whether data is absent, filtered or unavailable and offer one safe action | Never invent example records inside an official workspace. |

Buttons must say what happens: “生成並儲存草稿”, “確認發布並入帳”, “建立交接備份包”. Avoid “提交”, “確定”, or icon-only critical actions.

Dialog actions use one responsive grammar. Desktop presents a short, right-aligned action row; at `<= 900px`, the same semantic order becomes `sy-mobile-actions` with full-width controls of at least 48px. The safest exit or review action remains distinguishable from the consequential action, and source order follows consequence rather than visual convenience.

#### Sing Yin tactile component grammar

The interface may use Uiverse Elements broadly **only through one rewritten Sing Yin grammar**. Coverage may be extensive; visual dialects may not. The production source does not paste component HTML, use Uiverse global class names, load a Uiverse script, or make each page look like a different contributor's portfolio. It extracts a small interaction principle, maps it to the project tokens and Quasar state model, then supplies the missing accessibility and reliability states.

The current reference set is deliberately bounded:

| Reference pattern | Accepted idea | Rejected／rewritten behaviour |
|---|---|---|
| `adamgiebl / massive-insect-65` | Inset edge, shallow elevation and a press sink for the primary family | Fixed blue, monospace type, 56px-only sizing and 2px hover travel |
| `andrew-demchenk0 / afraid-squid-51` | Offset depth that visibly compresses on press | Heavy black neobrutalist border, 4px travel and a one-off component geometry |
| `Jay-9527 / weak-dingo-78` | A clearly separated track and thumb for switches | Hidden zero-size control without a visible project focus contract, generic green and 400ms timing |
| `Gautammsharma / massive-rabbit-40` | Checked, hover, focus and disabled states remain part of one checkbox | Standalone Material colour and selectors; production remains the semantic Quasar control |
| `Lanicet / fluffy-otter-43` | Inset progress track and rounded real fill | Infinite fabricated percentage animation; progress is driven only by actual workflow state |
| `Li-Deheng / shy-moth-10` and `JkHuger / little-falcon-22` | Directional public-login feedback and a calm encrypted-loading pulse | Multi-arrow decoration, looping colour spectacle, generic classes and motion-only meaning |

Attribution is retained in `NOTICE.md`; local source comments identify the adapted family. Uiverse remains a design reference and MIT source archive, not a runtime dependency.

The shared token owner is `design_system/tokens.v1.json`; generated `sing-yin-tokens-v1.css` exposes one set of control tokens—`--sy-control-edge`, `--sy-control-highlight`, `--sy-control-shadow`, `--sy-control-shadow-hover`, `--sy-control-outline-shadow` and `--sy-control-danger-shadow`—with separate light／dark values. `sing-yin-theme-v1.css` consumes those tokens for the shared component selectors. Quasar props remain the semantic API: `color=primary` is Primary, `outline` is Secondary, `flat` is Tertiary, `negative` is Destructive and `sy-button-attention` is Attention. Primary fill selectors must positively require `.bg-primary`; generic outline／hover rules must explicitly exclude `.text-negative` and `.sy-button-attention`. This semantic cascade rule prevents a broad visual rule from silently recolouring destructive or recovery actions. Pages must not recreate shadows, gradients or transition timings inline.

Quasar's palette is a **framework fill bridge**, not the complete design palette. `bg-primary`, `bg-positive`, `bg-negative` and `bg-info` normally carry white text, while `bg-warning` carries dark text; their values must therefore remain fill-safe in both themes. Dark-mode outline／flat foregrounds are intentionally lighter component tokens and must not be fed back into those filled utilities. The current bridge is: action fill `#35647C`／`#47758B`, stable fill `#0F766E`, danger fill `#963C35`／`#9A4A43`, info fill `#35647C`, and warning fill `#F0C96A`. CSS child-content rules supply dark outline action `#9BC2D2`, stable `#72D6C7`, danger `#D98F87` and attention `#F0C96A`. Browser evidence must measure the rendered label against the rendered surface rather than merely confirming that two colours differ.

All members of the family share these rules:

1. Geometry stays at 12px for buttons／fields, 44px minimum target and 48px for stacked phone actions. Hover never changes layout or label width.
2. A leading icon may sit in a small tonal well on Primary／Secondary controls, but critical text remains visible. Icon-only controls require an accessible name and use the compact tool family, not the prominent CTA shadow.
3. Fine-pointer hover may rise by 1px and deepen an existing shadow. Press sinks by 1px and compresses the shadow. Coarse pointers do not depend on hover; reduced-motion removes transforms while retaining colour, edge and state text.
4. Sidebar items, header utilities, bottom navigation, round tools, disabled, busy and loading controls are explicitly excluded from prominent elevation. Busy controls expose real `aria-busy`／disabled semantics and cannot be clicked twice.
5. Danger never hides its label or expands an icon over the text. Attention and danger are semantic states, not alternatives chosen for visual variety.
6. A switch keeps a real labelled control, visible focus, a track/thumb position cue and a non-colour label. Checkbox and radio retain focus, checked, indeterminate and disabled states.
7. Fields use restrained inset depth and a four-pixel soft focus halo in addition to the visible focus outline. Placeholder text never becomes the label.
8. Tabs gain a quiet active surface without becoming separate floating cards. Progress tracks are inset, but the fill represents a real value or an explicitly indeterminate operation; no decorative infinite progress is admitted.
9. CSS is the normal implementation path. Do not attach per-button pointer listeners or GSAP timelines merely to reproduce a hover effect; runtime motion is reserved for state transitions that CSS cannot truthfully express.
10. Button labels use sentence case; uppercase is reserved for short kickers and section labels. An uploader is a neutral input surface, never a competing primary CTA. Notifications use the same stable／info／attention／danger fills, icon and plain-language next step as the page that triggered them.
11. Filled danger is reserved for the last consequential remove／overwrite confirmation. Sign-out, cancel, close and ordinary navigation remain neutral even when they end a session or leave a screen.

Component acceptance requires desktop light, desktop dark, 390px and 320px mobile evidence; keyboard focus; primary／secondary／tertiary／attention／danger／disabled／busy examples; notification and uploader states; no console or page errors; no unintended overlap or horizontal overflow; 44px phone targets for buttons, toggles, checkboxes, radios and clickable rows; rendered label contrast of at least 4.5:1; static reduced-motion behaviour; and bounded DOM, listener and heap evidence. Shadow values must use the assigned shared tokens rather than page-local values, and pressed controls must return to idle without residual transform. A more dimensional appearance does not waive any of these checks.

The grammar governs the whole interface through component families, not page-by-page decoration:

| Family | Shared contract | Deliberate limit |
|---|---|---|
| Actions | Same 12px geometry, 44／48px target, semantic colour, focus, press, busy and disabled states | Only the current primary action receives the strongest emphasis; no persistent tilt or drift. |
| Form controls | One field surface, focus halo, labelled checkbox／radio and track-thumb switch language | A placeholder, colour or thumb position never carries meaning alone. |
| Navigation | Common active marker, quiet surface and predictable icon weight | Header, sidebar and phone tabs never imitate prominent CTAs. |
| Data | Stable table grid, tab hierarchy, honest progress and Chinese-name authority | No background imagery, ornamental gradients or fabricated percentages. |
| Feedback | Semantic stable／attention／danger／neutral badge and recovery language | Status colour never becomes an arbitrary icon palette. |
| Surfaces | One border, radius and elevation scale for cards, sheets and dialogs | Nested cards require a real change of ownership or task; no page-local shadow dialect. |
| Sacred reading | Independent scripture typography, indigo／parchment／gold and generous reading rhythm | Its distinct language never leaks into operational controls. |

When a new component is introduced, its owner must first assign it to one of these families. If none fits, update this specification and the shared tokens before styling the page. A new Uiverse reference is accepted only when it fills a documented interaction gap and can be rewritten into this grammar without adding a new visual dialect.

### Forms

Archive confirmation must name both sides of the consequence: the active person is removed from future selection, while historical rosters, fairness entries, and audit evidence remain. It must also state when the interface has no immediate undo; a generic “Are you sure?” is insufficient.

- Group fields according to the decision the operator is making, not database columns.
- Label every field; placeholder text is supplementary only.
- Show the smallest helpful instruction immediately before the first field.
- Validate at submit and state what to repair in user language.
- Repair predictable omissions before opening a progress state: focus the missing Chinese name, class, availability, published-duty adjustment reason, substitute, draft-change reason, or week-start field and keep the current context visible. A pre-generation leave reason is intentionally optional and is stored as absent rather than treated as an error. The workflow still owns Monday validation and repeats all domain validation as the final safety boundary.
- Snapshot identifiers and operator-entered reasons before the first asynchronous yield. A progress overlay must process exactly the choice that was visible when the operator pressed the action button.
- For actions longer than a brief interaction, show a calm blocking progress dialog connected to the action; prevent duplicate clicks. Use an honest phase message rather than a fictional percentage when the workflow cannot report one.
- An optimistic conflict is not a generic failure and never offers “save again”. When a prefect or reviewed draft changed in another browser, keep the operator's intent visible, explain that newer data won, and offer reload／review as the safe next action.
- A published-duty leave adjustment follows visible steps: choose the original duty, load and choose a qualified substitute (or deliberately retain a vacancy), then record the reason. Each phone field and action is full-width and touch-safe; the reason field keeps the unique accessible label and receives focus when it is missing.
- A file import separates **parsing**, **mapping**, **preview**, and **write**. The file name, row／column count, selected worksheet and every target mapping remain visible before preview. Optional DeepSeek assistance is labelled as a suggestion, states exactly which anonymous column metadata leaves the computer, and never visually outranks the manual selectors or preview action.
- A period-report preview is a read action, so its progress language says “checking” or “building”, never “saving”. Download actions use the already reviewed immutable model and do not imply that JSON created a backup or that scheduled allocation became verified service.

### Tables and roster matrix

- Keep table header, row height, alignment, and numerical treatment consistent.
- Names are left-aligned and use Chinese display names in every locale.
- Numerical workload is right-aligned and never relies on colour alone.
- Use a compact legend only when it changes a decision.
- On a published roster, the adjustment route is present but never visually equal to the normal weekly workflow.
- Group-schedule delivery is a two-step state change: prepare the immutable local PDF, then expose one primary native-file-share action and one download fallback. The share action says that WhatsApp is a selectable target; it never claims that a group was selected or a message was sent. The internal fairness-audit PDF remains download-only.
- A successful published-duty adjustment ends with a compact transaction receipt naming the debit, matching credit or deliberate vacancy, new roster version, reconciliation and verified backup. The next primary action is to export and share the corrected PDF, because an already distributed file cannot update in place.
- Desktop table and mobile cards must be generated from the same localized display model; changing one must not silently omit a duty in the other.
- Report charts always have an accessible table alternative. Fairness trend colour identifies series only; labels, values and source roster versions remain sufficient without colour. Chinese names remain authoritative in both interface languages and both report-PDF languages.

### Empty, error, success, and recovery states

- Empty: say what is absent and offer one clear safe next action.
- Dependency empty states must not open a dead-end confirmation. If package/restore depends on a verified snapshot, keep those controls visibly disabled, explain the dependency in the same card, and offer creation of the verified recovery point as the single active action.
- Trust warnings aggregate and classify; they do not dump diagnostics. Show a restrained amber status surface with a count and safe category labels, never raw exceptions, backup contents, student data, or a public-upload suggestion. A valid path may stay usable beside an invalid-snapshot warning.
- Trust checks may use bounded read-only parallelism, but never a visual shortcut or stale cache. Preserve newest-first presentation and show a loading state only if measured verification exceeds an ordinary navigation response; do not invent progress percentages.
- Error: identify the blocked condition and the repair path; never expose a raw implementation exception.
- Stale routes are recoverable states, not generic failures. A missing roster after restore or from an old bookmark uses a calm status surface, explains the likely context without claiming data loss, and offers two explicit destinations: current rosters and verified-backup settings. A draft opened through a published-adjustment URL must show no writable form and return the operator to review/publish.
- Error references: when a safe repair cannot be determined in the UI, show one bilingual next step and a short `OP-...` support reference. The corresponding rotating local log may contain only controlled action metadata, duration, exception type, and code location—never names, leave reasons, form values, roster rows, or PDF content.
- Partial success: if SQLite committed but the required snapshot failed, never use the ordinary error colour/copy or invite a retry. Use a persistent warm-amber recovery surface, state that the data took effect, say “do not repeat”, retain one OP reference, and offer exactly two actions: reload to review or open backup settings. The underlying roster page remains inert behind the modal.
- Success: name the saved result and what has changed—for example, “週表已發布，公平帳本已入帳並完成備份。”
- Recovery: state what will be restored, what safety snapshot is created first, and that the selection must be verified.
- Sharing: the confirmation must enumerate the exact outgoing whitelist and the excluded operational categories. The created-link dialog says the decryption key is shown once; revoked/expired/incomplete links collapse to one non-diagnostic bilingual recovery state.

### Practice-mode identity

- Practice mode is a persistent operational state, never a toast or colour-only hint. A compact amber status band appears in the same location on every page with an icon, explicit heading, and one-sentence consequence.
- Light mode uses warm paper amber with dark brown text; dark mode uses matte umber with pale gold text. Both remain solid, image-free, and visually separate from teal success and blue primary actions.
- At phone width the band becomes part of normal document flow so it cannot cover navigation or the current action.
- Practice and maintenance may both be true during a transition. They share one ordered `sy-status-stack`; neither banner may cover, replace, or visually merge with the other.
- Practice PDF identity repeats in filename, document body, and footer. The marker does not rely on colour and stays independent from the selected output language.

### Unified Guest identity

- Guest is a temporary NiceGUI application mode, not a second Practice Mode. Practice Mode is a durable isolated rehearsal with its own SQLite, audit, backup and restore; Guest uses a bounded process-memory adapter, fictional fixture, signed per-tab snapshot token and no official persistence.
- A concise identity seal states “fictional data / this tab / 30 minutes / no official write” in Traditional Chinese first with complete English support. The statement remains visible at phone width and does not rely on colour.
- Directory, leave controls, roster preview, demonstration publication, fairness explanation and PDF／JSON actions use the same calm workbench grammar and routes as Admin. Restricted AI, import, upload, external music, official share, backup／restore and permanent settings use one consistent `RESTRICTED` or `PRECOMPUTED` state; they are never secured only by hiding a control.
- The bilingual Guest PDF is A4 landscape, keeps all names Chinese, carries an unmistakable `DEMO` identity and is generated in memory behind a one-shot `no-store` download. Retention begins only if the visitor explicitly saves it.
- A refresh may restore only the newest valid signed token for the exact live session／workspace／tab. Duplicate-tab allocation, invalid-token fallback, expiry, logout, revocation and origin-restart cleanup must remain understandable without exposing token or storage internals in normal UI copy.

---

## 8. Motion and sound

Motion is feedback, not decoration. The visual style remains calm when motion is disabled.

### 8.1 Vector animation media contract

- **No GIF animation:** animated `.gif` files must not be introduced as backgrounds, illustrations, icons, loading indicators, empty states, button feedback, onboarding media, or fallbacks. GIF cannot meet this product's requirements for scalable edges, theme-aware colour, controllable timing, reduced motion, and efficient state-driven playback.
- **SVG is the default animated-art format:** use local, sanitised SVG plus CSS／Web Animations for icons, simple line or shape transitions, progress symbols, and short state feedback. SVG must not contain scripts, remote references, embedded tracking, required text, student data, or a raster frame sequence disguised as vector artwork.
- **Lottie is reserved for justified complexity:** use a local, versioned Lottie JSON asset only when layered vector sequencing would be materially clearer or more maintainable than SVG. Do not load Lottie from a public CDN, do not embed external images, and do not add a Lottie runtime until an approved production component actually needs it. The runtime must be lazy-loaded, pinned, same-origin, disposable on route teardown, and measured by the existing performance gate.
- **Motion remains semantic:** SVG／Lottie playback must be triggered by a real entrance, interaction, progress, success, attention, or explanatory state. It may be one-shot or state-controlled; decorative infinite loops, ambient motion, autoplay spectacle, false progress, bouncing and motion-only meaning remain prohibited.
- **Accessible fallback is mandatory:** `prefers-reduced-motion: reduce` shows the meaningful final or static first frame immediately and removes nonessential transitions. Required meaning remains in semantic HTML with a visible label or accessible name; decorative vectors are `aria-hidden`. A failed animation runtime falls back to the same static SVG／DOM state—never to GIF and never to an empty control.
- **Theme and quality parity:** an illustration whose palette cannot be token-driven must ship as deliberate light／dark SVG or Lottie companions using the same semantic slot and composition. Both themes, keyboard focus, touch, high zoom, mobile width and reduced motion require browser evidence. Vector use does not relax contrast, data-placement, privacy, or image-pair rules.
- **Performance ownership:** optimise SVG paths and Lottie layers, remove hidden artboards and unused keyframes, avoid filters that force large continuous repaints, and prefer transform／opacity animation. Any exceptional asset or runtime cost requires a browser trace and an explicit entry in this living standard.

Shared CSS motion tokens are the only default timing vocabulary: `--sy-motion-press: 90ms`, `--sy-motion-state: 180ms`, and `--sy-motion-layer: 260ms`. Components may use the longer documented narrative／feedback timings below only for their named purpose; scattered `.16s`／`.22s`／`.32s` literals are not a local design language.

| Moment | Motion | Duration |
|---|---|---:|
| Button press | Scale/opacity acknowledgement | 120ms |
| Tab or segmented state | Position-preserving content change | 180ms |
| Current Weekly Pulse step | One-time subtle emphasis on state change | 180–220ms |
| Dialog / confirmation | Fade and small vertical settle | 220ms |
| Pointer-reactive contextual surface | Up to 2px lift + local cursor light | 180–220ms |
| Non-sensitive narrative surface | One-time opacity/12px settle when it first enters view | 360–440ms |
| Grouped evidence cards | One-time 45ms stagger, capped at eight children | 360ms per item |
| Semantic operation feedback | Short action/stable/attention pulse at the active control | 500ms total |
| Action icon intent | Directional, navigation, confirm, transfer, create, edit, play or attention cue inside the active control | 90–180ms |
| Consequential local operation | Preparing → safely processing → finalising progress state | No invented duration |
| Page navigation | No theatrical transition; preserve orientation | 0–180ms |

- CSS uses the standard easing `cubic-bezier(.2, .8, .2, 1)`. The local GSAP runtime uses matching `power2.out`/`power1.out` curves for one-shot narrative entry, capped group stagger, cursor smoothing, and semantic feedback pulse.
- GSAP is locally vendored and same-origin; it has no data, navigation, policy, persistence, or network responsibility. `IntersectionObserver` starts a surface only once, while `MutationObserver` discovers NiceGUI-rendered content without polling the application state. The runtime owns an idempotent disposer, disconnects both observers, aborts pointer listeners, removes generated nodes, and uses `gsap.matchMedia()` so a live reduced-motion or pointer-capability change can revert enhancements safely.
- Material icon names are hydrated into stable semantic motion roles—`forward`, `back`, `navigation`, `refresh`, `confirm`, `download`, `upload`, `exchange`, `create`, `edit`, `toggle`, `play`, `search`, `danger`, `attention`, or neutral `signal`. The role describes the action rather than the page, so the same Dashboard, roster, directory, save, publish, download or edit action behaves consistently throughout the product.
- Icon feedback has complete control states: hover and keyboard focus express intent; press acknowledges input; a one-shot `navigation` state confirms route selection; busy and disabled remain still; accepted work may emit one short `working`, `success`, `attention` or silent `error` response at the initiating control. A single delegated recent-action reference survives a progress dialog taking focus, remains bounded in time, and is cleared safely; hydration uses the shared mutation observer and CSS state selectors rather than per-button listeners.
- Static evidence, team, architecture and metric cards must not masquerade as controls. On a fine pointer, only their explanatory icon may make a restrained response; the card surface remains still unless it contains a real link or action. A labelled process-map node may rise by at most 2px because its response helps the reader follow a sequence, but it must not gain a pointer cursor or imply navigation.
- Respect `prefers-reduced-motion`: skip GSAP entry/stagger/pulse motion, remove hover transforms and nonessential transitions, and keep the final content immediately visible. If GSAP cannot load, the runtime fails open to a static interface after a bounded retry rather than blocking the page.
- Sound remains opt-in and quiet. Navigation, accepted long-operation start, and successful completion may use short semantic cues; no hover, page-load, error, or background sound may play automatically. Visual feedback remains available when sound is off.
- Music is a separate comfort layer whose local player may make one visible page-ready attempt at a browser-local default of 50%, and always offers immediate pause/off controls. The 50% level is a starting point rather than forced loudness: a versioned migration upgrades only exact legacy 24%／35% defaults, while every other operator-selected level is preserved. When two routes resolve to the same local track, the next route restores that track's session position and playing／paused state instead of restarting it; this continuity uses bounded `sessionStorage`, never the roster database or permanent browser storage. A YouTube player must remain fully visible with native controls, never autoplay, and never sit behind a form, name, table, warning, roster, fairness record, or PDF. Public playlist playback does not require sign-in; optional API search and saved playlist names must never carry student data.
- No GSAP ScrollTrigger, pinning, looping animation, parallax, bouncing icons, or ambient video.

### Hover and press response

- Primary buttons rise by at most 1px on hover and compress slightly on press.
- Community component libraries are references, not a replacement design system. Uiverse-derived ideas enter only through the tactile component grammar in section 7: project tokens, scoped Quasar selectors, complete focus／touch／busy／disabled states and a static reduced-motion fallback. The original contributor colours, generic global class names, layout-changing hover, disappearing labels, fake progress and decorative looping effects are deliberately excluded.
- Active Weekly Pulse cards may rise by at most 2px on hover; pending cards remain still.
- Daily verse and workbench surfaces may gain a slightly deeper shadow on hover, but must never shift surrounding layout.
- Background artwork is static. Its purpose is atmosphere, not animation.
- Fine-pointer devices may show a restrained radial light only on a real link/action container or a deliberately editorial co-creation surface. Static workflow steps, architecture layers, onboarding, handover, storage explanations, tables, warnings and evidence cards must not glow or lift, because that creates a false click affordance.
- Buttons and expansion headers use a pointer cursor. Disabled actions use `not-allowed`; static tables, roster cells, names, warnings, and fairness data never gain a pointer cursor or floating transform.
- Sidebar items and expansion headers remain anchored: they do not drift, tilt or rotate. Responsiveness comes from the internal icon story, surface colour, border and focus ring, so navigation never appears physically unstable.
- Touch devices do not run hover transforms. Under `prefers-reduced-motion: reduce`, hover translation is removed and the cursor light is not rendered.
- A coarse-pointer press may run one in-place semantic icon story and restore the source glyph after a bounded delay. It must not rotate, drift, move the button, loop, delay activation, or run when reduced motion is requested.
- Hover tooltips are suppressed on coarse pointers; the same controls retain their explicit accessible names.

---

## 9. Accessibility and quality gates

### 9.0 Performance and resource budgets

The executable budgets are owned by `scripts/verify_runtime_performance.py`; this table mirrors that source and must change in the same commit whenever the script changes.

| Measurement | Maximum |
|---|---:|
| Initial transferred resources | 6 MiB |
| Largest single resource | 3 MiB |
| Initial resource count | 140 |
| Forced-GC heap growth after repeated interaction or route cycling | 10 MiB |
| DOM node growth | 160 |
| JavaScript listener growth | 100 |
| Mobile horizontal overflow | 0 px |

Public, Admin and Guest flows are measured separately. A lower synthetic number never justifies removing authorization checks, recovery controls, readable fonts or honest progress. Images reserve intrinsic dimensions, active atmosphere assets remain below 250 KB unless a trace justifies an exception, and route-specific media is not eagerly loaded outside its approved context.

Every visual refinement must meet all gates:

- Traditional Chinese and English labels are complete; Chinese prefect names remain Chinese.
- Direct Scripture quotations identify and use Traditional Chinese RCUV 2010（神版）and English NKJV; the canonical validator must block a release on wrong metadata or unverified/missing text.
- Light and dark mode preserve the same content, control order and state meaning as well as text, border, chart, and status contrast; paired-theme treatment may not hide or relocate an action in only one appearance.
- Keyboard focus is visible on buttons, fields, tabs, and links.
- Standalone links, buttons, summaries and Quasar clickable controls have 44px or larger practical targets on touch devices. Inline links inside running text retain the WCAG target-size exception; it is not an excuse for a compact standalone action.
- Icons have adjacent text or an accessible label; decorative icons are hidden from assistive technology.
- Colour is never the only carrier of status.
- Browser smoke captures desktop light, desktop dark, and mobile views after a component-class change.
- Automation for a new candidate records one device matrix: 256×700 zoom/reflow, 320×760 reduced-motion, 390×844 portrait, 768×1024 and 820×1180 adaptive touch-tablets, 1024×768 desktop-shell touch-tablet, 1440×1024 full desktop and 844×390 phone landscape. `verify_nicegui_mobile.py` supplies phone／tablet evidence and `verify_nicegui_ui.py` supplies the full-desktop member. Together they verify that the 900px breakpoint never exposes both navigation shells, then check the one-line mobile top bar, `Dashboard / Rosters / Prefects / More` bottom navigation, secondary-route semantics, focus transfer, scrollable More drawer, safe-area and `visualViewport` keyboard clearance, 44px standalone targets, card/table information parity, both languages/themes, one-shot touch feedback, reduced motion, forced colours and no unintended document overflow. A script name or screenshot is not pass evidence until the exact source appears in the final release report. Formal acceptance repeats 200% zoom, keyboard, rotation and safe-area behaviour on physical iPhone Safari and Android Chrome.
- Under `forced-colors: active`, navigation and mobile table-card boundaries use system `Canvas`, `CanvasText` and `Highlight` semantics with no shadow-dependent meaning. Current, focus and disabled states remain distinguishable without project palette colours.
- Browser evidence fails on either a console error or an uncaught `pageerror`; a visually correct screenshot cannot conceal a broken event handler.
- PDF remains print-first and is not redesigned by web-only decoration.

### 9.1 Reliability and fluidity gate

Design quality includes the behaviour underneath the surface.

- Page handlers request work; `roster_policy`, `roster_core`, and `roster_workflow` remain the owners of rules, selection, transactions, ledger effects, backups, and restore.
- Consequential local work runs outside the UI event loop with a persistent, bilingual progress dialog. It must prevent repeated submission and describe real phases rather than claim a precise duration.
- Candidate lists and final save validation use the same availability, leave, role, same-day uniqueness, and no-consecutive-duty constraints. A recommendation is never treated as sufficient proof at save time.
- Publication claims a draft with a conditional database update before it writes ledger rows. UI-level duplicate-click prevention is helpful, but the persistent transaction remains the final single-winner protection across browser tabs or concurrent local clients.
- Prefect writes, pre-generation leave changes, draft generation and manual draft correction begin with SQLite `BEGIN IMMEDIATE`. Prefect update／archive and manual draft correction also compare the reviewed version, so stale forms reload and review rather than overwrite newer state.
- Restore uses a host-wide exclusive maintenance marker plus payload-free operation leases. It waits for active operations in every application process to drain, rejects new writes, preflights the complete SQLAlchemy／Alembic schema and fairness state on a clone, and preserves a recovery marker only when automatic rollback cannot be proven safe.
- `/healthz` and deployment readiness require SQLite quick-check, the complete current table contract and the current Alembic head. A readable partial database is degraded, not “healthy”.
- Mutable music／playlist catalogues use a path-scoped read／modify／write lock and atomic, fsynced replacement. JSON preferences are not roster state, but they must still resist truncation under concurrent UI clients.
- A failed backup, checksum mismatch, or unverified restore is visible as an operation failure. The interface must not present a success state for a partially protected write.
- Browser mutation checks use an explicitly isolated SQLite database and backup directory; no visual test may create a roster or package from a real school database.
- Before a release candidate is accepted, one browser-driven isolated write pipeline must prove the real sequence: fictional import, declared leave, draft generation, manual correction, single publication, bilingual PDF delivery, published Chinese native-file-share handling with download fallback, published-duty adjustment, authoritative receipt and versioned corrected-PDF delivery, ledger/audit/backup evidence, handover package, and restore into a second isolated database.
- Final machine evidence is orchestrated by `scripts/verify_release_candidate.py`, which must create its own disposable paths, include Cloudflare Worker Deno contracts, desktop and independent mobile browser gates, the committed-without-backup drill, strict snapshot trust checks, and leave a failed—not partial-pass—report if any gate fails. Release fingerprinting includes `cloudflare/` JavaScript／JSONC, and repository hygiene blocks untracked release-sensitive source from being omitted. This machine report complements rather than replaces Head Study Prefect and teacher-advisor acceptance.
- The live rc20 baseline is bound to tag `v1.2.0-rc.20`, commit `e3d84858abfe23714929a87c4bcf76e55999ce7c` and fingerprint `93c6c93866c617862c790a4ed939d9acbe789dcdfaf512c9519aff9e0b4e6d3a`; its 14／14 gates comprise 839 Python tests, 3 motion contracts and 40 Worker contracts, and the controlled Windows switchover is complete. Supervised Head Study Prefect and teacher-advisor acceptance remains open. Any source change after rc20 requires a new immutable candidate and exact deployment evidence; rc20 evidence cannot be reused to claim the newer design is live.
- Runtime performance evidence measures both repeated component use and representative route navigation followed by return to the Dashboard. Heap, DOM-node and listener growth must stay bounded after garbage collection; a single fast first render is insufficient evidence of lifecycle quality.
- Acceptance evidence must remain legible as responsibility, not vanity metrics: map each requirement to a direct test/browser artifact and a named human decision. A test count, architecture diagram, or `pass` badge must never imply that real names, print legibility, school fairness practice, encrypted custody, or external-access approval were checked by software.
- Handover readiness uses a compact three-column desktop grid and one-column phone sequence; never render each small status as an oversized full-width card. Machine evidence and human acceptance are visually paired but semantically separate. Pass, running, stale, failed, missing, and unreadable states require icon, heading, explanatory copy, and a safe next action rather than colour alone.
- Every change to policy-facing UI, long-operation flow, theme-specific imagery, or recovery must add/adjust focused tests, run the full suite, and capture the relevant desktop light/dark and mobile evidence.

---

## 10. Implementation roadmap

### Phase A — token consolidation

1. Replace scattered visual values with the token roles in this document.
2. Remove remaining generic shadows, arbitrary gradients, and conflicting component radii.
3. Audit light/dark contrast and focus states.

### Phase B — Weekly Pulse and page hierarchy

1. Refine dashboard spacing, stage hierarchy, and current-state presentation.
2. Recompose roster workspace around prepare → decide → confirm.
3. Give empty states a direct next action.

### Phase C — operational components

1. Standardize form sections, tables, dialogs, statuses, and confirmation patterns.
2. Add correct loading states to consequential writes.
3. Improve mobile table and navigation behavior without hiding evidence.

### Phase D — finishing quality

1. Apply purposeful micro-motion and opt-in sound only where it confirms a real result.
2. Capture light, dark, desktop, and mobile comparison screenshots.
3. Conduct the Head Study Prefect and teacher advisor acceptance checklist.

No phase may weaken roster policy, persistent fairness, backup verification, privacy, bilingual parity, or the print layout.

### Phase E — measured performance and lifecycle quality

1. Web UI uses Inter plus platform-native Hong Kong／Traditional Chinese fallbacks; the large Noto TTF files remain for deterministic PDF embedding, not cold browser download.
2. Shared theme CSS is a versioned same-origin token layer followed by compatibility and responsive layers, so navigation reuses browser-cached assets instead of repeating the design system in every HTML response.
3. The optional music controller is a single persistent non-modal panel. Opening and closing it must not mount another dialog tree; Escape and the close control return focus to the trigger.
4. Phone layout places one responsive “next safe step” immediately after Daily Verse and hides the repeated three-card flow inside the workbench at 600 px or below. The compact workbench summary and start guide remain available; the verse stays first and the only current action remains inside the first viewport.
5. `verify_runtime_performance.py` is a release gate for cold transfer, largest resource, resource count, forced-GC heap growth, DOM nodes, JavaScript listeners, console errors, representative routes, and mobile overflow. Motion on reduced-motion or touch input adds no pointer-light node.

### Phase F — evidence-led visual refinement

1. The interface follows the **Service Weave／服事經緯** direction: slate blue means action, teal means identity or verified stability, gold belongs to devotional reading, and ordinary explanatory icons remain neutral.
2. Platform and Engineering keep at most one evidence kicker each; repeated all-caps eyebrow labels are not a substitute for hierarchy. Capability names describe work directly and do not invent offices or departments.
3. The sidebar remains one shared structural slot with paired light/dark artwork. Dark mode must reference `sidebar-stewardship-dark-v1.webp` and use a translucent near-black veil that preserves visible material texture without reducing navigation contrast.
4. New artwork is added only when it explains an otherwise unclear orientation or empty state. A future seeded static Service Weave light/dark pair may replace generic showcase still life, but no runtime canvas, looping background, extra corporate title or decorative illustration button is approved.
5. Release evidence maps `pass → stable`, `running → action`, `stale/missing/unreadable → attention`, and `fail → danger`; engineering gates inherit that real evidence tone rather than appearing teal by default.
6. School crests use the reviewed alpha PNGs in transparent, borderless containers. Navigation and co-creation marks may use a restrained theme-aware shadow, but never a white tile, rim or rounded image plate; their local image transition is immediate so the first frame does not look washed out.
7. The Guest reference lane retains the six non-sensitive orientation destinations—Platform & Team, Engineering & Quality, System Architecture & Trust, Getting Started, Operator Guide and Daily Verse—alongside the same fictional weekly-work routes used by Admin. These pages may explain the product and demonstrate bounded operations, but they never expose official names, rosters, backup paths or audit payloads.
8. Contextual audio is a persistent operator preference, not a page-completion signal. Every supported page context and light/dark recommendation must resolve to at least one local track, while browser verification waits for semantic DOM／URL／workflow results rather than `networkidle` after audio has been unlocked.
9. Daily Verse is a distinct sacred reading sequence—read, reflect, pray, return to service—not a decorative dashboard card. Its gold／indigo language, paired theme imagery and spacious typography remain subordinate to Scripture and must support reduced motion.

### Phase G — operational hierarchy and semantic continuity

1. Every operational domain has one stable hub. Child routes must render a route trail, an explicit destination-based return action and the same ordered workflow model; browser history is never the only way back.
2. The roster sequence is generate → review／export → published-duty adjustment → history. The current step uses text, geometry and `aria-current`, not colour alone; unavailable future steps remain visible but non-interactive so the operator understands what comes next.
3. Operational surfaces use the full available content workspace. Constrain inner text or form measures for readability, not the outer card; a wide empty field beside a narrow action card is a layout defect unless the space has an explicit secondary purpose.
4. Header utilities share one surface grammar. Language, appearance, sound, music and logout each retain a visible container, 44px practical target, keyboard focus and bilingual accessible name.
5. A semantic icon animation must tell a short state story: menu → back, calendar → confirmed event, manual edit → verified change, book → open reading, help → illuminated idea. It may swap a framework glyph through an opacity／scale transition, but must not depend only on translation, move or rotate its host, or loop. Reduced motion and forced colours resolve to the static meaningful state; touch may play one bounded opacity／scale story and then restore the source glyph.
6. Browser matrix, public Viewer and PDF use one duty-position presentation source. Duty names remain canonical English in both locales; prefect names remain Chinese. Translation text must never become a policy or database key.
7. Reasons are optional explanatory context. Leaving one blank must not remove version checks, command receipts, audit, fairness reconciliation, backup obligations or destructive-action confirmation.

---

## 11. Governance

This file is the design source of truth for the active NiceGUI application, but it is a **living executable standard rather than a permanent creative restriction**. A better design direction may replace an earlier rule when evidence shows clearer operation, stronger accessibility, better brand coherence or lower maintenance risk. The change is complete only when the shared tokens, reusable components, every affected route, both themes, both languages, responsive states, reduced-motion behaviour, tests and this document all move together. A one-page exception is not an evolution of the system; it is design drift.

When a UI decision changes, update this file and `PROJECT_STATUS.md` together. Retire or migrate superseded selectors and components instead of leaving two competing visual dialects. A change needs an explicit rationale if it:

- adds a new colour role, radius, shadow level, or icon family;
- adds or changes a material texture, blend mode, approved placement or paired theme asset;
- changes the primary weekly workflow order;
- changes an accessibility, dark-mode, or motion rule;
- introduces or changes SVG／Lottie animation media, its runtime, fallback, theme pairing, or performance budget;
- introduces a visual treatment that could be mistaken for liquid glass or an Apple asset;
- changes a print/PDF hierarchy.
- changes Guest versus authenticated-Admin meaning, Access login/logout, signed-principal trust, snapshot binding, the public-share data whitelist, or link lifecycle.
- changes the canonical Scripture source, RCUV 2010（神版）／NKJV contract, verification status, or the distinction between a direct quotation and a labelled service principle.

Before implementation, the maintainer should record: the operator moment, the affected component, the intended evidence, and the screenshots/tests required. This keeps visual quality maintainable for future 首席導學風紀 instead of relying on personal taste.

---

## 12. Initial acceptance questions

1. On opening the dashboard, can a new 首席導學風紀 see the daily verse and the one next safe action without scrolling or guessing?
2. Does the current stage look distinct because it is operationally current, rather than merely more colourful?
3. Can a student use every important form, table, and confirmation in light mode, dark mode, and at mobile width?
4. Does the product feel calm and precise without blur, excessive teal, or decorative animation?
5. Can the teacher advisor recognise the same system purpose in the UI, PDF, audit, backup, and handover path?
6. Does one canonical URL make guest read-only state, Admin login, authenticated editor state, and Log out consequence unambiguous without relying on colour alone?


### Ambient pointer light (non-interactive paper)

- Action surfaces keep `.sy-pointer-reactive` with lift + glow.
- Non-interactive editorial paper uses `.sy-pointer-ambient` + `.sy-pointer-light--ambient`: softer radial follow-light, no translateY, default cursor, and a calm `:focus-within` halo for keyboard users inside policy panels.
- Opt-in panels use `data-sy-ambient-light="true"` (Assist. mode and history-priority policy panels).
- Forbidden on workflow static steps (`.sy-flow-step`, `.sy-architecture-layer`, `.sy-storage-lifecycle`) and tables.
- `prefers-reduced-motion` and coarse pointers still remove the light entirely.
