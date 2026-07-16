# Extractable Draft Components

This catalogue identifies reusable visual entities for Superdesign drafts. Props describe state or navigation differences between uses; translated labels, icon names, class names, and visual styling remain hardcoded unless stated otherwise.

## Layout components

| Name | Source | Description | Extractable props | Hardcoded |
|---|---|---|---|---|
| AppShell | [`page_shell`](../../nicegui_app/ui/shell.py) | Shared drawer, header, status stack, main canvas, and mobile navigation. | `titleKey`, `activePath`, `musicContext` | Navigation groups, crest slot, utility order, page-context spine |
| SidebarNavigation | [`page_shell`](../../nicegui_app/ui/shell.py) | Grouped desktop navigation and mobile More drawer. | `activePath`, `isOpen`, `accessMode` | Group order, icons, feedback group |
| HeaderUtilityBar | [`page_shell`](../../nicegui_app/ui/shell.py) | Chapter context and compact language, sound, appearance, media, and session controls. | `chapter`, `pageTitle`, `showMusic`, `accessMode`, `theme`, `soundEnabled` | Control order and icon vocabulary |
| StatusStack | [`page_shell`](../../nicegui_app/ui/shell.py) | Ordered global practice, Guest, and maintenance banners. | `showPractice`, `showGuest`, `maintenanceState` | Banner order and status icons |
| MobileBottomNavigation | [`_render_mobile_tabbar`](../../nicegui_app/ui/shell.py) | Persistent Dashboard, Rosters, Prefects, and More navigation. | `activePath`, `moreOpen` | Destinations, labels, icons, four-column layout |
| ReferenceTOC | [`render_page_toc`](../../nicegui_app/ui/reference_navigation.py) | Compact anchor list for long reference pages. | `items` | Heading treatment and link style |
| ReferencePager | [`render_reference_pager`](../../nicegui_app/ui/reference_navigation.py) | Previous and next reading-lane navigation. | `previous`, `next` | Direction labels and card geometry |

## Basic components

| Name | Source | Description | Extractable props | Hardcoded |
|---|---|---|---|---|
| ToneBadge | [`_tone_badge`](../../nicegui_app/ui/page_shared.py) | Semantic status pill. | `text`, `tone` | Tone vocabulary and CSS |
| FlowStep | [`_render_flow_step`](../../nicegui_app/ui/page_shared.py) | Numbered stage in the weekly sequence. | `number`, `title`, `detail`, `state`, `icon`, `actionLabel`, `actionEnabled` | State geometry and disabled copy |
| OperationHint | [`_render_operation_hint`](../../nicegui_app/ui/page_shared.py) | Purpose-and-method cue before an operator decision. | `body`, `icon` | Aside layout |
| EmptyState | [`_render_empty_state`](../../nicegui_app/ui/page_shared.py) | Empty-result guidance with one optional action. | `title`, `body`, `icon`, `actionLabel`, `illustrated` | Alignment and action hierarchy |
| RouteRecoveryState | [`_render_roster_route_state`](../../nicegui_app/ui/page_shared.py) | Safe recovery from an unavailable detail route. | `title`, `body`, `icon`, `primaryLabel`, `primaryHref`, `secondaryLabel`, `secondaryHref` | Two-action consequence order |
| ResponsiveTable | [`_render_responsive_table`](../../nicegui_app/ui/page_shared.py) | Desktop table and phone grid using the same display model. | `columns`, `rows`, `rowKey` | Breakpoint and Quasar table modes |
| MobileRosterCards | [`_render_mobile_roster_cards`](../../nicegui_app/ui/page_shared.py) | Day-grouped duty cards. | `days`, `rows`, `statusTone` | Field order and mobile card grammar |
| MobileDirectoryCards | [`_render_mobile_prefect_cards`](../../nicegui_app/ui/page_shared.py) | Compact identity and fairness cards. | `rows`, `supportStates` | Field order and role-pill geometry |
| RestrictedCapability | [`render_restricted_capability`](../../nicegui_app/ui/page_access.py) | Calm unavailable-action explanation. | `title`, `body`, `icon` | Inline-empty treatment |
| FeedbackChannel | [`_render_feedback_channel`](../../nicegui_app/ui/page_shared.py) | Support and project-source panel. | `compact` | Action order and safe-contact note |
| ProgressDialog | [`_run_with_progress`](../../nicegui_app/ui/page_shared.py) | Indeterminate working sheet for consequential operations. | `title`, `workingCopy`, `icon`, `isOpen` | Progress treatment and dismissal rules |

## Feature and editorial components

Some entries are currently inline page sections. Their listed source is the extraction boundary.

| Name | Source | Description | Extractable props | Hardcoded |
|---|---|---|---|---|
| DailyVersePanel | [`dashboard_page`](../../nicegui_app/ui/page_routes/home.py) | Compact sacred start above the weekly workbench. | `scripture`, `reference`, `reflectionTitle`, `reflectionBody`, `tone`, `expanded` | Sacred colour and type language |
| DevotionalChapel | [`devotional_page`](../../nicegui_app/ui/page_routes/home.py) | Full reading hero plus reflection, prayer, and preparation cards. | `scripture`, `reference`, `reflection`, `prayer`, `tone` | Three-card composition and return action |
| WeeklyPulseWorkbench | [`dashboard_page`](../../nicegui_app/ui/page_routes/home.py) | Current status, three flow steps, and safe next action. | `currentStage`, `hasDirectory`, `latestStatus`, `recentItems` | Three-stage sequence |
| RosterGenerationPanel | [`rosters_page`](../../nicegui_app/ui/page_routes/weekly.py) | Week, fairness, availability, and generation controls. | `week`, `historyWeight`, `leaveItems`, `canGenerate` | Control order and explanatory hierarchy |
| RosterReviewSurface | [`roster_detail_page`](../../nicegui_app/ui/page_routes/weekly.py) | Roster display with status, publication, correction, and export actions. | `status`, `rows`, `canPublish`, `canCorrect`, `canShare` | Consequence order and table-card pairing |
| AdjustmentStepper | [`adjustment_detail_page`](../../nicegui_app/ui/page_routes/weekly.py) | Original assignment, substitute, reason, and confirmation flow. | `assignment`, `candidates`, `selectedCandidate`, `reason`, `state` | Three-step order |
| DirectoryFairnessWorkspace | [`prefects_page`](../../nicegui_app/ui/page_routes/people.py) | Directory and fairness tabs with editing and report actions. | `activeTab`, `rows`, `selectedItem`, `empty`, `accessMode` | Tab order and action grouping |
| HandoverReadinessGrid | [`handover_page`](../../nicegui_app/ui/page_routes/stewardship.py) | Readiness checks for directory, roster history, and verified recovery. | `checks` | Three-card grid and tone mapping |
| AcceptancePanel | [`handover_page`](../../nicegui_app/ui/page_routes/stewardship.py) | Machine evidence beside required human acceptance. | `machineState`, `passed`, `total`, `humanRequired` | Two-column evidence model and checklist order |
| RecoverySettingsPanel | [`settings_page`](../../nicegui_app/ui/page_routes/stewardship.py) | Recovery status, integrity warnings, package preparation, and restore. | `status`, `warnings`, `hasVerifiedRecovery`, `selectedItem` | Card order and danger confirmation |
| AccessPermissionCards | [`render_access_control_console`](../../nicegui_app/ui/access_control.py) | Operator and viewer access explanation with link management. | `configured`, `publishedOptions`, `activeItems` | Two-card permission model |
| PlatformMetricCard | [`platform_page`](../../nicegui_app/ui/page_routes/showcase.py) | Compact live project fact. | `label`, `value`, `tone` | Monospace evidence style |
| CapabilityCard | [`platform_page`](../../nicegui_app/ui/page_routes/showcase.py) | One capability in the team operating model. | `title`, `body`, `icon` | Card geometry |
| EngineeringGate | [`engineering_page`](../../nicegui_app/ui/page_routes/showcase.py) | Ordered release or quality gate. | `index`, `title`, `body`, `state` | Numbered evidence grammar |
| ServiceLifelineStage | [`system_architecture_page`](../../nicegui_app/ui/page_routes/showcase.py) | One station in the six-stage service lifeline. | `index`, `title`, `body`, `result`, `icon` | Lifeline connector and stage order |
| ArchitectureLayerCard | [`system_architecture_page`](../../nicegui_app/ui/page_routes/showcase.py) | One system layer with responsibility and trust boundary. | `title`, `body`, `icon` | Layer-card treatment |
| TrustEvidenceCard | [`system_architecture_page`](../../nicegui_app/ui/page_routes/showcase.py) | Verifiable trust claim with evidence label. | `title`, `body`, `evidence`, `tone` | Evidence-divider grammar |
| CoCreationPanel | [`_render_co_creation`](../../nicegui_app/ui/page_shared.py) | Creator identity, authorship, and Codex closing note. | translated text and optional destination visibility | Media slots, crest slot, signature hierarchy |

## Extraction guidance

- Extract layout and basic components before page-level feature sections.
- Preserve semantic states instead of exposing raw colour props.
- Use abstract fixture content for all people, rosters, dates, evidence counts, and recovery items.
- Preserve Traditional Chinese and English text expansion in the same component geometry.
- Preserve desktop and phone variants as one component contract rather than separate products.
- Keep service calls, persistence, permission enforcement, and export generation outside DraftComponents.
