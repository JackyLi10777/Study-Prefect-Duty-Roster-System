# Pages — current dependency trees

These trees describe the actual NiceGUI composition used for the faithful baseline.

## 1. Public entrance

Source outline (text):
    gateway public route
    ├── product identity / Service Weave mark
    ├── editorial value proposition
    ├── Admin sign-in action
    ├── Guest demonstration action
    ├── published-share guidance
    ├── Daily Verse excerpt
    └── theme preference handoff

## 2. Dashboard `/`

Source: `nicegui_app/ui/page_routes/home.py:29-162`.

Source outline (text):
    page_shell("/")
    ├── Daily Verse hero (dashboard_verse, refresh, reflection)
    ├── three-stage weekly workflow
    │   ├── generate draft
    │   ├── review / publish / export
    │   └── published-duty absence
    ├── current roster state / empty state
    └── safe next action

## 3. Rosters `/rosters`

Source: `nicegui_app/ui/page_routes/weekly.py:175-668`.

Source outline (text):
    page_shell("/rosters")
    ├── directory-required recovery state
    ├── storage lifecycle
    ├── workflow navigation
    ├── Generate tab
    │   ├── week date
    │   ├── Assist assignment policy
    │   ├── history fairness multiplier + chart
    │   ├── vacancies/rules
    │   ├── pre-generation leave
    │   └── generate command
    └── Adjust/Edit tab
        └── current roster versions/actions

## 4. Roster detail `/rosters/{id}`

Source: `nicegui_app/ui/page_routes/weekly.py:674-901`.

Source outline (text):
    page shell
    ├── explicit return/workflow navigation
    ├── status/version/week metadata
    ├── shared roster matrix
    ├── manual draft edit controls when draft
    ├── publish/export actions
    ├── withdraw published action when eligible
    └── adjustment destination

## 5. Prefects `/prefects`

Source: `nicegui_app/ui/page_routes/people.py:701-1332`.

Source outline (text):
    page shell
    ├── directory search/filter/edit
    ├── CSV/XLSX upload with bounded preview
    ├── paste/import assistant states
    ├── responsive directory table/cards
    ├── fairness panel and trends
    └── bilingual PDF + JSON evidence downloads

## 6. Handover `/handover`

Source: `nicegui_app/ui/page_routes/stewardship.py:31-232`.

Source outline (text):
    page shell
    ├── paired atmosphere hero
    ├── page-local contents
    ├── operator checklist
    ├── new-year directory handover
    ├── verified backup/restore evidence
    └── acceptance responsibility

## 7. Platform `/platform`

Source: `nicegui_app/ui/page_routes/showcase.py:43-270`.

Source outline (text):
    page shell
    ├── product mark + functional identity
    ├── live operational snapshot
    ├── real Study Prefect Team roles
    ├── operating map
    ├── capabilities and solutions
    ├── service principles
    └── resources/co-creation close

## 8. System architecture `/system-architecture`

Source: `nicegui_app/ui/page_routes/showcase.py:573-732`.

Source outline (text):
    page shell
    ├── editorial hero + TOC
    ├── PageContext / capability boundary
    ├── policy/core/workflow/persistence layers
    ├── Guest/Admin adapters and lifecycle
    ├── health/readiness/recovery
    └── extension rules + reference pager

## 9. Daily Verse `/devotional`

Source: `nicegui_app/ui/page_routes/home.py:309-369`; selection source `nicegui_app/ui/devotional.py` (complete, 59 lines).

Source outline (text):
    page shell
    ├── sacred hero with theme-paired image
    ├── tone selector + refresh
    ├── bilingual verse, reference and translation attribution
    ├── reading/reflective context
    ├── prayer companion
    └── return to weekly service

## 10. Support `/support`

Source: `nicegui_app/ui/page_routes/support.py`.

Source outline (text):
    page shell
    ├── browser-only Public/Viewer report path
    ├── Guest non-persistent report path
    ├── Admin local incident bundle path
    ├── redaction and attachment guidance
    └── support reference / recovery state
