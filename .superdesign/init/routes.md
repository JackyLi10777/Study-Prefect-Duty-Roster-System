# Routes — canonical current contract

Canonical registry: `nicegui_app/ui/page_catalog.py` (complete source, 305 lines). Registration side effects are imported once by `nicegui_app/ui/page_routes/__init__.py`:

Source outline (python):
    from . import access, home, people, showcase, stewardship, support, weekly
    __all__ = ["access", "home", "people", "showcase", "stewardship", "support", "weekly"]

## PageDefinition schema

Source outline (python):
    class PageKind(str, Enum):
        OPERATIONS = "operations"
        STORY = "story"
        EVIDENCE = "evidence"
        REFERENCE = "reference"
        SACRED = "sacred"

    @dataclass(frozen=True)
    class PageDefinition:
        route: str
        title_key: str
        navigation_group: str
        icon: str
        page_kind: PageKind
        music_context: str
        required_capability: Capability | None
        visible_access_modes: frozenset[AccessMode]
        mobile_primary: bool = False

## Workbench route map

| Route | Kind | Icon | Music | Primary purpose |
|---|---|---|---|---|
| `/` | operations | `space_dashboard` | dashboard | Daily Verse + next safe weekly action |
| `/rosters` | operations | `calendar_month` | weekly | generate, review, publish, export, adjust |
| `/prefects` | operations | `groups` | people | directory, import, fairness and reports |
| `/handover` | operations | `handshake` | handover | annual handover and recovery duties |
| `/access-control` | operations | `admin_panel_settings` | settings | access explanation and controls |
| `/settings` | operations | `settings` | settings | session/system preferences and recovery |
| `/platform` | story | `domain` | architecture | mission, roles, capability and continuity |
| `/system-architecture` | reference | `account_tree` | architecture | boundaries, lifecycle and reference |
| `/engineering` | evidence | `build_circle` | architecture | verified release/recovery evidence |
| `/getting-started` | reference | `play_circle` | getting_started | first-use route |
| `/guide` | reference | `help_outline` | guide | operator procedures |
| `/devotional` | sacred | `menu_book` | devotional | reading, reflection, prayer, return to service |
| `/support` | operations | `support_agent` | guide | local incident report and recovery guidance |

Additional parameterised routes are owned by `page_routes/weekly.py` for roster detail and adjustments, by `page_routes/people.py` for audit/reporting, and by the gateway for Public/Viewer entry. They must project the same shell and capability policy.

## Navigation groups

1. getting started
2. weekly operations
3. people and fairness
4. handover and governance
5. administration
6. contextual help
7. trust/resources portal

Only Dashboard, Rosters, and Prefects are mobile-primary. All other routes remain reachable through More/drawer and explicit workflow navigation.
