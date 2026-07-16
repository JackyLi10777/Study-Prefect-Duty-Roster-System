# Routes

NiceGUI uses decorator-based route registration rather than a file-based frontend router.

## Registration chain

1. [`nicegui_app/main.py`](../../nicegui_app/main.py) imports the UI facade.
2. [`nicegui_app/ui/pages.py`](../../nicegui_app/ui/pages.py) imports the route package.
3. [`nicegui_app/ui/page_routes/__init__.py`](../../nicegui_app/ui/page_routes/__init__.py) imports all six route modules.
4. Each route module registers functions with `@ui.page`.

## Page map

| URL | Page function | Source | Layout active path | Summary |
|---|---|---|---|---|
| `/` | `dashboard_page` | [`home.py`](../../nicegui_app/ui/page_routes/home.py) | `/` | Daily Verse, next action, Weekly Pulse, and recent rosters |
| `/dashboard` | `dashboard_alias` | [`home.py`](../../nicegui_app/ui/page_routes/home.py) | redirect | Compatibility redirect to Dashboard |
| `/getting-started` | `getting_started_page` | [`home.py`](../../nicegui_app/ui/page_routes/home.py) | `/getting-started` | First-use steps and reference map |
| `/guide` | `operator_guide_page` | [`home.py`](../../nicegui_app/ui/page_routes/home.py) | `/guide` | Operator guidance and troubleshooting table |
| `/devotional` | `devotional_page` | [`home.py`](../../nicegui_app/ui/page_routes/home.py) | `/devotional` | Full sacred-reading view with reflection, prayer, and return action |
| `/rosters` | `rosters_page` | [`weekly.py`](../../nicegui_app/ui/page_routes/weekly.py) | `/rosters` | Generate a weekly draft and inspect roster history |
| `/rosters/new` | `generate_roster_page` | [`weekly.py`](../../nicegui_app/ui/page_routes/weekly.py) | redirect | Compatibility redirect to the roster workspace |
| `/rosters/{roster_week_id}` | `roster_detail_page` | [`weekly.py`](../../nicegui_app/ui/page_routes/weekly.py) | `/rosters` | Draft review, correction, publication, export, and published view |
| `/adjustments` | `adjustments_page` | [`weekly.py`](../../nicegui_app/ui/page_routes/weekly.py) | redirect | Compatibility redirect to the roster workspace |
| `/rosters/{roster_week_id}/adjustments` | `adjustment_detail_page` | [`weekly.py`](../../nicegui_app/ui/page_routes/weekly.py) | `/rosters` | Published-duty leave adjustment and substitute confirmation |
| `/prefects` | `prefects_page` | [`people.py`](../../nicegui_app/ui/page_routes/people.py) | `/prefects` | Directory, fairness, reports, editing, and imports |
| `/audit` | `audit_page` | [`people.py`](../../nicegui_app/ui/page_routes/people.py) | redirect | Compatibility redirect to Prefects |
| `/handover` | `handover_page` | [`stewardship.py`](../../nicegui_app/ui/page_routes/stewardship.py) | `/handover` | Successor steps, school-year rollover, readiness, and acceptance evidence |
| `/settings` | `settings_page` | [`stewardship.py`](../../nicegui_app/ui/page_routes/stewardship.py) | `/settings` | Music preferences, recovery status, handover package, and restore |
| `/access-control` | `access_control_page` | [`access.py`](../../nicegui_app/ui/page_routes/access.py) | `/access-control` | Operator and viewer access model plus public-link management |
| `/platform` | `platform_page` | [`showcase.py`](../../nicegui_app/ui/page_routes/showcase.py) | `/platform` | Team operating model, capabilities, solutions, and resources |
| `/engineering` | `engineering_page` | [`showcase.py`](../../nicegui_app/ui/page_routes/showcase.py) | `/engineering` | Engineering facts, architecture layers, and release gates |
| `/system-architecture` | `system_architecture_page` | [`showcase.py`](../../nicegui_app/ui/page_routes/showcase.py) | `/system-architecture` | Service lifeline, system layers, trust evidence, and FAQ |

## Shared layout

All non-redirect pages use [`page_shell`](../../nicegui_app/ui/shell.py). The active path controls navigation highlighting and the stable page slug. The optional music context selects only a page-level listening profile; it does not receive route records.

## Route-module ownership

- [`home.py`](../../nicegui_app/ui/page_routes/home.py): Dashboard, onboarding, guide, devotional.
- [`weekly.py`](../../nicegui_app/ui/page_routes/weekly.py): Weekly roster workflow and adjustments.
- [`people.py`](../../nicegui_app/ui/page_routes/people.py): Directory, fairness, reports, and imports.
- [`stewardship.py`](../../nicegui_app/ui/page_routes/stewardship.py): Handover and settings.
- [`access.py`](../../nicegui_app/ui/page_routes/access.py): Access-control entry page.
- [`showcase.py`](../../nicegui_app/ui/page_routes/showcase.py): Platform, engineering, and architecture narratives.

Non-visual application endpoints are intentionally outside this design route map.
