# Professional Design System

**Project:** Sing Yin Study Prefect Duty Roster System  
**Version:** 1.1 – living design, interaction, and reliability standard  
**Status:** Active design source of truth  
**Primary audience:** 負責日常操作的當任首席導學風紀、主要在完成後核對的顧問老師、未來維護者及實作代理人

---

## 1. Purpose

This document defines the visual and interaction standard for the local-first NiceGUI application. Its job is not to make a school system look fashionable. Its job is to help a 首席導學風紀 make a fair weekly decision calmly, understand its consequence, and hand the system to the next leader without depending on technical help.

The visual direction is inspired by the discipline behind contemporary iOS and Apple product experiences: clear hierarchy, precise type, considered materials, responsive feedback, and restraint. It is an original Sing Yin system. It must not copy Apple screens, assets, trademarks, liquid glass, or proprietary visual effects.

### Design thesis

> **A quiet school operations desk: one clear responsibility at a time, with enough evidence to act confidently.**

The signature interaction is **值週節奏 / Weekly Pulse**: the interface makes the current stage, the safe next action, and the durable result visible. It is not an animation for decoration; it is a consistent operational landmark across the dashboard, roster workspace, publication, adjustment, and handover.

### Author voice and handover narrative

The system has one human authorial voice: **李創杰，2026–2027 年度首席導學風紀**. Author introductions, motivation, design values, handover letters, project history, and co-creation conclusions must be written in his first person (`我` / `I`). They must not describe him at a distance as though an unrelated corporate narrator owns the project.

Codex is named as 李創杰's co-creator and technical colleague. A separately labelled “Codex 的結語” may use Codex's own first person, but it must not replace, merge with, or impersonate 李創杰's voice. Statements about the two-person team use `我與 Codex` / `Codex and I` when spoken by 李創杰.

Operational instructions, safety rules, current machine evidence, architecture contracts, and acceptance checklists remain direct, objective, or imperative. First-person authorship must make the handover more human without turning verifiable technical state into personal opinion. Traditional Chinese uses natural Hong Kong written language; the complete English version preserves the same speaker and meaning rather than reverting to third person.

### Feedback channel

The public project feedback address is `s10777@syss.edu.hk`, and the canonical source/documentation destination is `https://github.com/JackyLi10777/Study-Prefect-Duty-Roster-System`. They appear together as a restrained persistent sidebar resource group and as a fully explained panel in the Operator Guide and architecture/co-creation page. Both actions must be available in both languages and keyboard reachable; main-content actions remain at least 44px high. GitHub opens in a new tab with `noopener noreferrer`, while email uses the local mail client.

Feedback is distinct from technical evidence. Ordinary suggestions may use email directly; a failure should first preserve its OP/REQ reference. Copy asks for the reference and a short description only, never names, leave details, rosters, PDFs, databases, backups, screenshots, or complete logs.

### 2026.07 adaptive direction — Quiet Precision / 安靜精準

The next design level is not “more Apple-like” or “more decorated”. It is a synthesis of the most durable ideas in Apple HIG, Material Design 3, Nordic editorial interfaces, Japanese restraint, and mature independent productivity software:

1. **Recognition before style:** the operator must recognise the current stage, primary action, and consequence before noticing the visual treatment.
2. **One geometry grammar:** navigation, controls, cards, sheets, and status markers share a small radius, spacing, icon, and border vocabulary. Similar meaning produces similar shape.
3. **Quiet action colour:** primary actions use a desaturated slate-blue that remains distinct from teal identity and verified states. Bright electric blue is removed because it dominates warm materials and creates a plastic visual break.
4. **Solid material hierarchy:** background, quiet group, working surface, and raised decision layer are separated by contrast, border, and restrained shadow. Blur and transparency are unnecessary.
5. **Motion has three speeds:** 90 ms press acknowledgement, 180 ms state change, and 260 ms layer/entry transition. Exit is faster than entry; motion uses transform/opacity and remains interruptible.
6. **Controls form a dock:** page utilities are visually grouped as one compact, solid tool cluster. The current navigation item uses text weight plus a slim position rail, not colour alone.
7. **Density follows consequence:** routine scanning stays compact; publication, restore, archive, and fairness consequences receive more space and plain-language explanation.
8. **Calm is not emptiness:** blank space is retained where it separates decisions. Contextual imagery may enrich approved non-sensitive scenes, but it never fills space that should communicate order.

This direction deliberately moves beyond brand imitation. It treats HIG and Material guidance as behavioural evidence, then expresses it through an original Sing Yin operational language.

### Current design mandate

This is the complete standing direction for future iterations. It replaces any tendency to make a generic dashboard, a literal Apple imitation, a HyperOS imitation, or a decoration-heavy template.

1. **Quiet operational luxury:** the normal application is a calm, orderly school work desk. Borrow the discipline of Muji-like material honesty—warm paper, linen, light timber, soft daylight, and generous empty space—without borrowing branding, product images, logos, or retail styling.
2. **Original digital precision:** use the useful principles of high-quality product interfaces—clear hierarchy, responsive feedback, coherent geometry, and readable system states—without copying Apple, Xiaomi, or any other company’s screens, assets, trade dress, or sounds.
3. **A separate sacred language for Scripture:** Daily Verse is a devotional pause rather than a work card. It must be visibly distinct, more contemplative, bilingual, dignified, and spiritually meaningful, while remaining compact enough that the weekly duty workflow begins immediately below it.
4. **One real weekly sequence:** Generate draft → review/publish and export → published-duty leave adjustment. Closely related tasks belong together; navigation must never make an operator hunt across unrelated pages.
5. **Purposeful imagery only:** use original, local, non-identifying imagery as low-opacity context for devotion, onboarding, handover, and empty states. Never place it behind forms, tables, student names, fairness data, PDFs, controls, or warnings. No text, people, school badge, watermark, or fake product UI inside generated imagery. Every enabled scene must have a deliberate light-mode and dark-mode companion asset, the same semantic slot and crop logic, independently tuned opacity/readability veils, and browser screenshots in both themes. Single-asset exceptions are not permitted.
6. **Calm feedback, not theatre:** hover, press, one-time state changes, a short dialog settle, optional quiet success sound, honest progress phases, and operator-started quiet music are allowed. No looping animation, parallax, autoplay audio/video, fake loading percentage, forced ambient sound, bouncing icon, or motion that impedes reading.
7. **Accessibility and language are non-negotiable:** Traditional Chinese is primary, English is complete, names stay Chinese in every locale, keyboard focus is clear, touch targets are practical, reduced motion is honoured, and light/dark themes meet contrast requirements for text, icons, charts, tables, and system states.
8. **Reliability is part of the experience:** a polished surface cannot disguise a failed save. UI changes must preserve policy ownership, persistent `history_weight`, publish-once ledger posting, leave-adjustment auditability, checksum-verified snapshots, managed restore, local-first privacy, and clear error/empty/confirmation states.
9. **Privacy before distribution:** no student data is sent to generated imagery, third-party tools, or public URLs. Cloudflare exposure remains prohibited until Cloudflare Access and a teacher-approved security decision exist.

### Design languages that intentionally differ

| Context | Design language | Must feel like | Must not become |
|---|---|---|---|
| Weekly roster work | Quiet operations desk: neutral surfaces, slate action, teal verified state, compact factual type | Calm, dependable, easy to scan | A KPI dashboard, a dense admin console, or a decorative template |
| Daily Verse | Sacred reading chamber: deep indigo, warm parchment/gold, serif reading type, measured space, low movement | A moment of reflection before service | A generic hero banner, a sermon slide, or a dark-themed work card |
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

The school crest is an official identity asset, not generated atmosphere artwork. User-supplied PNG masters remain at project root; semantic delivery copies are retained under `nicegui_app/assets/brand/` and selected by context rather than by an ambiguous `logo.png` filename:

- `sing-yin-crest-favicon.png` — a 512×512 delivery copy for the browser favicon.
- `sing-yin-crest-navigation.png` — the purpose-sized 545×524 source for the 60×58 sidebar identity mark; using the supplied small master avoids repeated extreme downscaling.
- `sing-yin-crest-display-web.png` — a 640-pixel delivery copy for the architecture/co-creation seal.
- `sing-yin-crest-display-print.png` — the full 5983×5751 source reserved for PDF output.

The original alpha transparency is preserved; no JPEG conversion or automated background removal is allowed. Display the crest on a solid white identity surface in both themes so its white shield and dark-blue outline remain stable. Keep the favicon, navigation, display, and print paths centralized in `nicegui_app/config.py`; future replacements must update these semantic files, retain Chinese characters and English school name, and pass browser and PDF verification at their actual rendered sizes.

---

## 2. Confirmed state and decision brief

### Current state

The active NiceGUI application already has correct policy safeguards, bilingual support, light/dark mode, verified backups, print-ready PDFs, contextual hints, and a three-stage weekly workflow. The existing theme has a sound foundation—neutral surfaces, teal identity, restrained slate primary actions, rounded controls, and good contrast—but its presentation must continue converging on one composed product rather than a collection of useful cards.

### Head Study Prefect moment

At the start of a busy week, the operator needs to read the daily verse, see what stage the roster is in, make one safe action, and leave with confidence that the result is fair and recoverable. They should never have to scan a dense control panel, guess which color is actionable, or open several pages merely to understand the system state.

### Priority and trade-off

This is an **L2 workflow and visual-system improvement**. It should improve confidence, legibility, and handover before adding novelty. A dramatic theme, permanent animation, decorative illustrations, or excessive teal would make the system feel less serious and date faster. The priority is a consistent hierarchy and a distinctive operational rhythm.

### Strategy and evidence

The owner is `nicegui_app/ui/theme.py` plus `theme_markup.py` for tokens and component language, `nicegui_app/ui/page_routes/` plus `page_shared.py` for page hierarchy, and `nicegui_app/ui/i18n_catalog/` behind the stable `i18n.py` facade for bilingual copy. Every implementation phase must preserve policy boundaries, keyboard access, light/dark contrast, and the existing browser smoke coverage. Screenshots in both modes and at mobile width are required before a phase is accepted.

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

### Useful inheritance from the former Professional Teal reference

- Respectful spacing, low visual fatigue, semantic colour, light/dark parity, accessible focus, and a local-first professional tone.

### Deliberately changed from that reference

- The direction is no longer HyperOS. It is a more structured, Apple-inspired original system language.
- Primary action colour is a muted slate-blue; teal is deliberately restrained.
- No blanket card nesting, generic KPI tiles, or decorative depth.

---

## 5. Token system

### 5.1 Colour roles

| Token | Light | Dark | Purpose |
|---|---:|---:|---|
| `stable-teal` | `#0F766E` | `#72D6C7` | School identity and verified, published, completed, or settled states only |
| `action-slate` | `#35647C` | `#9BC2D2` | Links, outlined actions, current step, guidance and interactive icons |
| `button-action` | `#35647C` | `#47758B` | Filled primary button with white text; never used merely for decoration |
| `action-slate-soft` | `#E8F0F3` | `#1A2B34` | Current-step grouping and quiet action context; never a text-only state |
| `attention-amber` | `#8A5A00` | `#F0C96A` | Draft, missing prerequisite, practice mode, partial success or review needed |
| `danger-red` | `#B42318` | `#FF8A80` | Destructive, blocked or failed state only |
| `neutral-control` | `#5F6368` | `#C5C7CA` | Pending, inactive, ordinary navigation and non-status icons |
| `ink` | `#1C1C1E` | `#F5F5F7` | Important text |
| `secondary-ink` | `#6E6E73` | `#AEAEB2` | Supporting copy and metadata |
| `ground` | `#F2F2F7` | `#000000` | Page background |
| `surface` | `#FFFFFF` | `#1C1C1E` | Cards, sheets, dialogs, navigation |
| `surface-subtle` | `#E5E5EA` | `#2C2C2E` | Tables, quiet grouping, disabled treatment |
| `devotional-gold` | `#D3A930` | `#FFD60A` | Scripture only; never a general call to action |

Rules:

1. One screen has one blue primary action at most.
2. Teal may identify the application, a completed or verified state, and devotional anchors. It must not colour all buttons.
3. Warning and danger are semantic only. Never use them for visual variety.
4. Text meets WCAG AA contrast: 4.5:1 for normal text and 3:1 for large text or UI boundaries.

#### Component colour grammar

The interface never assigns colours icon by icon. A component first declares its semantic tone, and its icon inherits that tone:

| Semantic tone | Components | Examples |
|---|---|---|
| `action` | Filled/outlined CTA, current workflow step, progress, operation hint | Generate, save, export, open current draft |
| `stable` | Status badge or evidence only | Published, verified backup, completed step |
| `attention` | Status badge or recovery surface only | Draft ready, missing backup, practice, partial success |
| `danger` | Destructive action or failed status | Archive, remove, invalid/unreadable evidence |
| `neutral` | Pending state and ordinary utility | Waiting step, empty-state symbol, secondary navigation |

Equivalent actions keep one tone even when their content differs: the share-safe roster PDF and internal audit PDF are both export actions, so both use action slate. Status and action are not conflated: a draft badge is attention/action-context, while “open draft” remains an action control. Colour is always accompanied by text, icon, border, position or state wording.

Settings follows the same rule at section level. Interface audio, local music, and YouTube are peer configuration sections, so their top rule and heading icon all use action slate; YouTube becomes teal only where a badge explicitly says the connection is ready. Backup warnings and the entry into restore use attention amber. The final restore confirmation uses danger red because it replaces the active database, even though the workflow first creates a safety snapshot.

Full illustrated empty states are reserved for orientation moments where a new operator must understand how to begin, currently the dashboard and roster workspace before the first week exists. Music libraries, unavailable backups, recovery routes, and repeated empty panels use compact neutral guidance without imagery. This prevents one paired scene from repeating down a settings page and keeps warnings, forms, and recovery decisions visually unambiguous.

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
| 0 | Page ground and tables | Boundary only |
| 1 | Standard cards | Fine border + soft short shadow |
| 2 | Current action / open popover | Slightly stronger shadow and blue/teal state treatment |
| 3 | Confirmation dialog | Clear solid surface, stronger shadow, dimmed background |

Do not layer a card inside a card unless there is a real change of task or ownership.

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
- Recent history stays subordinate. It must not compete with the current work.

### 6.1.1 Daily Verse: sacred reading component

The Daily Verse is a distinct component, not a recoloured dashboard card.

- **Structure:** small book mark; bilingual devotional label; Scripture in serif reading type; reference; quiet refresh control; one progressively disclosed reflection. The main dashboard version remains compact; the `/devotional` page may use the fuller reading chamber.
- **Materials:** deep indigo surface, warm parchment text, restrained gold rule, and a local right-weighted contextual image. In light mode it uses `devotional-sacred-light-v1.webp`; dark mode uses `devotional-sacred-dark-v1.webp`.
- **Reading protection:** a solid left-to-right veil protects text; the image is never the sole contrast mechanism. Scripture may never sit on a busy crop, an animated layer, or a translucent glass panel.
- **Motion:** no automatic movement. Hover may deepen elevation only; verse refresh is an explicit action and changes content without an ornamental page transition.
- **Separation:** blue remains a work-action colour below. The Daily Verse uses gold and parchment only within its own surface, so it is recognisably sacred without turning the application into a themed template.
- **Direction:** the operator may choose `Follow appearance`, `Clear guidance`, or `Quiet comfort`. Follow appearance initially maps light mode to service, justice, wisdom, and witness; dark mode maps to prayer, care, perseverance, faithfulness, and spiritual formation. This is a recommendation rather than an emotional stereotype: the explicit operator choice persists, refresh remains manual, and the selected direction filters only already-polished bilingual entries.

### 6.1.2 Music atmosphere profiles

Music must remain operator-started and page-context-aware. The intended next extension is one `Follow appearance` preference plus two independently selectable profiles:

- **Bright focus:** gentle forward movement, clarity, hope, service, and the beginning of work; suitable for light-mode default recommendation.
- **Quiet reflection:** slower pacing, reassurance, patience, prayer, and handover; suitable for dark-mode default recommendation without implying sadness.

Appearance selects only the first recommendation when the operator has not chosen a profile. A saved profile overrides appearance until reset. Both profiles may contain several playlists, support sequential/shuffle playback, and remain subordinate to page context and the existing volume/no-autoplay controls. Do not add placeholder tracks: external playlists enter the product only after their exact public YouTube Music URLs and display names have been verified.

### 6.2 Roster workspace

The roster page follows a **prepare → decide → confirm** hierarchy:

1. State and week context.
2. Pre-generation leave and vacancy evidence.
3. Generate draft or choose a published adjustment.
4. Draft table as the inspection artifact.
5. Publication/adjustment confirmation at the moment of consequence.

The roster grid is an operational document, not a dashboard chart. Preserve the row/weekday/name structure, give headers a stable surface, and allow names to dominate cells. Avoid visual effects inside the table that reduce print or scan clarity. At phone width, render the same roster data as day-grouped duty cards: each card keeps the post, time, Chinese name, status, and workload together. Do not force a person to horizontally scroll to discover a name or use a different data source for the mobile presentation.

### 6.3 Directory, fairness, and settings

- **Directory:** show the active people list first; editing and archive actions are clearly secondary to identity accuracy. On a phone, render the same localized directory data as individual identity cards—Chinese name, form/class, role, availability, workload, and duty count—rather than clipping a seven-column table.
- **Import:** use a staged form—template, paste, validate, preview, import—rather than one large ambiguous text area.
- **Fairness:** position the explanation before the numbers. Data should answer “why”, not merely display totals.
- **Settings:** separate routine status from high-consequence recovery. Restore and export backup packages must remain confirmation-gated.

### 6.4 Responsive rule

- Desktop: content has a readable max width, not a full-width administrative spreadsheet.
- Tablet: two-column regions collapse only when each column would become too narrow to read.
- Mobile: primary action remains before secondary information; grids become ordered vertical lists. The roster uses day-grouped cards, not a horizontally clipped table, so every Chinese name, duty time, status, and workload is readable in one card.

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
3. Present the five-layer blueprint and eight release gates as semantic ordered lists. Connectors are CSS decoration only; reading order remains complete without them.
4. Use neutral surfaces, monospaced evidence numbers, slate action colour, and teal only for verified or durable outcomes. Dark mode receives separately checked text, border, and state contrast.
5. Keep the page read-only. It may consume display-safe release evidence but never workflow, roster, leave, fairness, backup path, or audit payloads.
6. On mobile, facts, blueprint layers, gates, capabilities, and evolution stages become one ordered vertical sequence without horizontal scrolling.

Enterprise references inform information order, not visual imitation. Platform, solutions, trust, resources, and company/team narratives must be translated into the Sing Yin context with original geometry and copy. A generated narrative image may support the non-sensitive operating-model story only when a same-composition light/dark pair is present; organisational meaning must remain in semantic HTML, never inside image text or a fake diagram.

---

## 7. Components and interaction patterns

### Navigation

- Group pages by real work: weekly work, people and fairness, handover and system, guides and devotional.
- Active navigation has a blue selection field and remains visible in both themes.
- Icons are one consistent Material outline family, supporting—not replacing—text.
- Limit primary navigation to the current operating map; archive old routes only as redirects for bookmarks.

### Buttons

| Kind | Use | Visual rule |
|---|---|---|
| Primary | The one next consequential action | Solid action blue, clear verb, 44px touch target |
| Secondary | A valid alternative or review path | Outline/quiet surface, same clear verb |
| Tertiary | Navigation or low-risk discovery | Flat text with icon only when it clarifies meaning |
| Destructive | Archive/irreversible action | Danger colour and confirmation |

Buttons must say what happens: “生成並儲存草稿”, “確認發布並入帳”, “建立交接備份包”. Avoid “提交”, “確定”, or icon-only critical actions.

### Forms

Archive confirmation must name both sides of the consequence: the active person is removed from future selection, while historical rosters, fairness entries, and audit evidence remain. It must also state when the interface has no immediate undo; a generic “Are you sure?” is insufficient.

- Group fields according to the decision the operator is making, not database columns.
- Label every field; placeholder text is supplementary only.
- Show the smallest helpful instruction immediately before the first field.
- Validate at submit and state what to repair in user language.
- Repair predictable omissions before opening a progress state: focus the missing Chinese name, class, availability, leave reason, substitute, draft-change reason, or week-start field and keep the current context visible. The workflow still owns Monday validation and repeats all domain validation as the final safety boundary.
- Snapshot identifiers and operator-entered reasons before the first asynchronous yield. A progress overlay must process exactly the choice that was visible when the operator pressed the action button.
- For actions longer than a brief interaction, show a calm blocking progress dialog connected to the action; prevent duplicate clicks. Use an honest phase message rather than a fictional percentage when the workflow cannot report one.
- A published-duty leave adjustment follows visible steps: choose the original duty, load and choose a qualified substitute (or deliberately retain a vacancy), then record the reason. Each phone field and action is full-width and touch-safe; the reason field keeps the unique accessible label and receives focus when it is missing.

### Tables and roster matrix

- Keep table header, row height, alignment, and numerical treatment consistent.
- Names are left-aligned and use Chinese display names in every locale.
- Numerical workload is right-aligned and never relies on colour alone.
- Use a compact legend only when it changes a decision.
- On a published roster, the adjustment route is present but never visually equal to the normal weekly workflow.
- Desktop table and mobile cards must be generated from the same localized display model; changing one must not silently omit a duty in the other.

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

### Practice-mode identity

- Practice mode is a persistent operational state, never a toast or colour-only hint. A compact amber status band appears in the same location on every page with an icon, explicit heading, and one-sentence consequence.
- Light mode uses warm paper amber with dark brown text; dark mode uses matte umber with pale gold text. Both remain solid, image-free, and visually separate from teal success and blue primary actions.
- At phone width the band becomes part of normal document flow so it cannot cover navigation or the current action.
- Practice PDF identity repeats in filename, document body, and footer. The marker does not rely on colour and stays independent from the selected output language.

---

## 8. Motion and sound

Motion is feedback, not decoration. The visual style remains calm when motion is disabled.

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
| Consequential local operation | Preparing → safely processing → finalising progress state | No invented duration |
| Page navigation | No theatrical transition; preserve orientation | 0–180ms |

- CSS uses the standard easing `cubic-bezier(.2, .8, .2, 1)`. The local GSAP runtime uses matching `power2.out`/`power1.out` curves for one-shot narrative entry, capped group stagger, cursor smoothing, and semantic feedback pulse.
- GSAP is locally vendored and same-origin; it has no data, navigation, policy, persistence, or network responsibility. `IntersectionObserver` starts a surface only once, while `MutationObserver` discovers NiceGUI-rendered content without polling the application state.
- Respect `prefers-reduced-motion`: skip GSAP entry/stagger/pulse motion, remove hover transforms and nonessential transitions, and keep the final content immediately visible. If GSAP cannot load, the runtime fails open to a static interface after a bounded retry rather than blocking the page.
- Sound remains opt-in and quiet. Navigation, accepted long-operation start, and successful completion may use short semantic cues; no hover, page-load, error, or background sound may play automatically. Visual feedback remains available when sound is off.
- Music is a separate, operator-started comfort layer. A YouTube player must remain fully visible with native controls, never autoplay, and never sit behind a form, name, table, warning, roster, fairness record, or PDF. Public playlist playback does not require sign-in; optional API search and saved playlist names must never carry student data.
- No GSAP ScrollTrigger, pinning, looping animation, parallax, bouncing icons, or ambient video.

### Hover and press response

- Primary buttons rise by at most 1px on hover and compress slightly on press.
- Active Weekly Pulse cards may rise by at most 2px on hover; pending cards remain still.
- Daily verse and workbench surfaces may gain a slightly deeper shadow on hover, but must never shift surrounding layout.
- Background artwork is static. Its purpose is atmosphere, not animation.
- Fine-pointer devices may show a restrained radial light that follows the pointer within Weekly Pulse, architecture, onboarding, handover, export, co-creation, and storage-explanation surfaces. The light is limited to the hovered surface and carries no information.
- Buttons and expansion headers use a pointer cursor. Disabled actions use `not-allowed`; static tables, roster cells, names, warnings, and fairness data never gain a pointer cursor or floating transform.
- Sidebar items may move horizontally by at most 3px so navigation feels responsive without changing layout. Expansion headers use the same 3px maximum and retain a visible keyboard focus ring.
- Touch devices do not run hover transforms. Under `prefers-reduced-motion: reduce`, hover translation is removed and the cursor light is not rendered.

---

## 9. Accessibility and quality gates

Every visual refinement must meet all gates:

- Traditional Chinese and English labels are complete; Chinese prefect names remain Chinese.
- Light and dark mode preserve text, border, chart, and status contrast.
- Keyboard focus is visible on buttons, fields, tabs, and links.
- Critical actions have 44px or larger practical targets on touch devices.
- Icons have adjacent text or an accessible label; decorative icons are hidden from assistive technology.
- Colour is never the only carrier of status.
- Browser smoke captures desktop light, desktop dark, and mobile views after a component-class change.
- PDF remains print-first and is not redesigned by web-only decoration.

### 9.1 Reliability and fluidity gate

Design quality includes the behaviour underneath the surface.

- Page handlers request work; `roster_policy`, `roster_core`, and `roster_workflow` remain the owners of rules, selection, transactions, ledger effects, backups, and restore.
- Consequential local work runs outside the UI event loop with a persistent, bilingual progress dialog. It must prevent repeated submission and describe real phases rather than claim a precise duration.
- Candidate lists and final save validation use the same availability, leave, role, same-day uniqueness, and no-consecutive-duty constraints. A recommendation is never treated as sufficient proof at save time.
- Publication claims a draft with a conditional database update before it writes ledger rows. UI-level duplicate-click prevention is helpful, but the persistent transaction remains the final single-winner protection across browser tabs or concurrent local clients.
- A failed backup, checksum mismatch, or unverified restore is visible as an operation failure. The interface must not present a success state for a partially protected write.
- Browser mutation checks use an explicitly isolated SQLite database and backup directory; no visual test may create a roster or package from a real school database.
- Before a release candidate is accepted, one browser-driven isolated write pipeline must prove the real sequence: fictional import, declared leave, draft generation, manual correction, single publication, bilingual PDF downloads, published-duty adjustment, ledger/audit/backup evidence, handover package, and restore into a second isolated database.
- Final machine evidence is orchestrated by `scripts/verify_release_candidate.py`, which must create its own disposable paths, include the independent committed-without-backup drill, run strict snapshot trust checks, and leave a failed—not partial-pass—report if any gate fails. This machine report complements rather than replaces Head Study Prefect and teacher-advisor acceptance.
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

---

## 11. Governance

This file is the design source of truth for the active NiceGUI application. When a UI decision changes, update this file and `PROJECT_STATUS.md` together. A change needs an explicit rationale if it:

- adds a new colour role, radius, shadow level, or icon family;
- changes the primary weekly workflow order;
- changes an accessibility, dark-mode, or motion rule;
- introduces a visual treatment that could be mistaken for liquid glass or an Apple asset;
- changes a print/PDF hierarchy.

Before implementation, the maintainer should record: the operator moment, the affected component, the intended evidence, and the screenshots/tests required. This keeps visual quality maintainable for future 首席導學風紀 instead of relying on personal taste.

---

## 12. Initial acceptance questions

1. On opening the dashboard, can a new 首席導學風紀 see the daily verse and the one next safe action without scrolling or guessing?
2. Does the current stage look distinct because it is operationally current, rather than merely more colourful?
3. Can a student use every important form, table, and confirmation in light mode, dark mode, and at mobile width?
4. Does the product feel calm and precise without blur, excessive teal, or decorative animation?
5. Can the teacher advisor recognise the same system purpose in the UI, PDF, audit, backup, and handover path?
