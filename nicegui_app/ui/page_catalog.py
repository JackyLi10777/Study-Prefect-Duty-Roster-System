"""Canonical workbench page and navigation contract.

Route handlers remain responsible for rendering their content.  This catalog
owns stable route identity, navigation grouping, iconography, music context,
access visibility, and the minimum capability needed to enter each page.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from nicegui_app.access_context import AccessMode, Capability, CapabilityPolicy


class PageKind(str, Enum):
    """The information posture of a page, independent of translated copy."""

    OPERATIONS = "operations"
    STORY = "story"
    EVIDENCE = "evidence"
    REFERENCE = "reference"
    SACRED = "sacred"


WORKBENCH_ACCESS_MODES = frozenset(
    {AccessMode.ADMIN, AccessMode.GUEST, AccessMode.LOCAL_MAINTENANCE}
)
NAVIGATION_GROUP_ORDER = (
    "nav_getting_started",
    "nav_weekly_operations",
    "nav_people_fairness",
    "nav_handover_governance",
    "nav_administration",
    "nav_contextual_help",
)
PORTAL_GROUP = "nav_trust_resources"


@dataclass(frozen=True)
class PageDefinition:
    """Stable page identity used by desktop and mobile shells."""

    route: str
    title_key: str
    navigation_group: str
    icon: str
    page_kind: PageKind
    music_context: str
    required_capability: Capability | None
    visible_access_modes: frozenset[AccessMode]
    mobile_primary: bool = False

    def is_visible_to(self, mode: AccessMode) -> bool:
        return mode in self.visible_access_modes

    def is_accessible_to(self, mode: AccessMode) -> bool:
        """Return the server-side navigation predicate for this page."""

        return self.is_visible_to(mode) and (
            self.required_capability is None
            or CapabilityPolicy.allows(mode, self.required_capability)
        )


PAGE_DEFINITIONS = (
    PageDefinition(
        route="/",
        title_key="dashboard",
        navigation_group="nav_weekly_operations",
        icon="space_dashboard",
        page_kind=PageKind.OPERATIONS,
        music_context="dashboard",
        required_capability=Capability.DEMO_DATA_READ,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
        mobile_primary=True,
    ),
    PageDefinition(
        route="/rosters",
        title_key="rosters",
        navigation_group="nav_weekly_operations",
        icon="calendar_month",
        page_kind=PageKind.OPERATIONS,
        music_context="weekly",
        required_capability=Capability.DEMO_DATA_READ,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
        mobile_primary=True,
    ),
    PageDefinition(
        route="/prefects",
        title_key="prefects",
        navigation_group="nav_people_fairness",
        icon="groups",
        page_kind=PageKind.OPERATIONS,
        music_context="people",
        required_capability=Capability.DEMO_DATA_READ,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
        mobile_primary=True,
    ),
    PageDefinition(
        route="/handover",
        title_key="handover",
        navigation_group="nav_handover_governance",
        icon="handshake",
        page_kind=PageKind.OPERATIONS,
        music_context="handover",
        required_capability=Capability.DEMO_DATA_READ,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
    PageDefinition(
        route="/access-control",
        title_key="access_control",
        navigation_group="nav_administration",
        icon="admin_panel_settings",
        page_kind=PageKind.OPERATIONS,
        music_context="settings",
        required_capability=Capability.SESSION_PREFERENCES_MODIFY,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
    PageDefinition(
        route="/settings",
        title_key="settings",
        navigation_group="nav_administration",
        icon="settings",
        page_kind=PageKind.OPERATIONS,
        music_context="settings",
        required_capability=Capability.SESSION_PREFERENCES_MODIFY,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
    PageDefinition(
        route="/platform",
        title_key="platform",
        navigation_group=PORTAL_GROUP,
        icon="domain",
        page_kind=PageKind.STORY,
        music_context="architecture",
        required_capability=None,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
    PageDefinition(
        route="/system-architecture",
        title_key="system_architecture",
        navigation_group=PORTAL_GROUP,
        icon="account_tree",
        page_kind=PageKind.REFERENCE,
        music_context="architecture",
        required_capability=None,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
    PageDefinition(
        route="/engineering",
        title_key="engineering",
        navigation_group=PORTAL_GROUP,
        icon="build_circle",
        page_kind=PageKind.EVIDENCE,
        music_context="architecture",
        required_capability=None,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
    PageDefinition(
        route="/getting-started",
        title_key="getting_started",
        navigation_group="nav_getting_started",
        icon="play_circle",
        page_kind=PageKind.REFERENCE,
        music_context="getting_started",
        required_capability=None,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
    PageDefinition(
        route="/guide",
        title_key="operator_guide",
        navigation_group="nav_contextual_help",
        icon="help_outline",
        page_kind=PageKind.REFERENCE,
        music_context="guide",
        required_capability=None,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
    PageDefinition(
        route="/devotional",
        title_key="devotional",
        navigation_group="nav_contextual_help",
        icon="menu_book",
        page_kind=PageKind.SACRED,
        music_context="devotional",
        required_capability=None,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
    PageDefinition(
        route="/support",
        title_key="report_problem",
        navigation_group="nav_contextual_help",
        icon="support_agent",
        page_kind=PageKind.OPERATIONS,
        music_context="guide",
        required_capability=None,
        visible_access_modes=WORKBENCH_ACCESS_MODES,
    ),
)


def page_definition(route: str) -> PageDefinition | None:
    """Return one canonical definition without guessing translated routes."""

    normalized = route if route == "/" else "/" + route.strip("/")
    return next((page for page in PAGE_DEFINITIONS if page.route == normalized), None)


def navigation_groups_for(
    mode: AccessMode,
) -> tuple[tuple[str, tuple[PageDefinition, ...]], ...]:
    """Build desktop navigation from the same ordered page catalog."""

    groups: list[tuple[str, tuple[PageDefinition, ...]]] = []
    for group in NAVIGATION_GROUP_ORDER:
        pages = tuple(
            page
            for page in PAGE_DEFINITIONS
            if page.navigation_group == group and page.is_accessible_to(mode)
        )
        if pages:
            groups.append((group, pages))
    return tuple(groups)


def portal_pages_for(mode: AccessMode) -> tuple[PageDefinition, ...]:
    """Return evidence and documentation destinations outside routine work."""

    return tuple(
        page
        for page in PAGE_DEFINITIONS
        if page.navigation_group == PORTAL_GROUP and page.is_accessible_to(mode)
    )


def mobile_navigation_for(mode: AccessMode) -> tuple[PageDefinition, ...]:
    """Build the compact mobile tab bar from the canonical page catalog."""

    return tuple(
        page
        for page in PAGE_DEFINITIONS
        if page.mobile_primary and page.is_accessible_to(mode)
    )


def navigation_item_tuples_for(
    mode: AccessMode,
) -> tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...]:
    """Compatibility view for code that still consumes simple item tuples."""

    return tuple(
        (
            group,
            tuple((page.route, page.title_key, page.icon) for page in pages),
        )
        for group, pages in navigation_groups_for(mode)
    )


def validate_page_catalog() -> list[str]:
    """Return every structural or capability problem in the page manifest."""

    errors: list[str] = []
    routes = [page.route for page in PAGE_DEFINITIONS]
    if len(routes) != len(set(routes)):
        errors.append("Page catalog contains duplicate routes")
    mobile_count = 0
    for page in PAGE_DEFINITIONS:
        if not page.route.startswith("/"):
            errors.append(f"Page route must be absolute: {page.route}")
        if page.navigation_group not in (*NAVIGATION_GROUP_ORDER, PORTAL_GROUP):
            errors.append(f"Unknown navigation group for {page.route}")
        if not page.title_key or not page.icon or not page.music_context:
            errors.append(f"Incomplete page presentation contract: {page.route}")
        if AccessMode.PUBLIC in page.visible_access_modes:
            errors.append(f"Workbench page must not expose PUBLIC shell access: {page.route}")
        if page.required_capability is not None:
            for mode in page.visible_access_modes:
                if not CapabilityPolicy.allows(mode, page.required_capability):
                    errors.append(
                        f"{page.route} requires {page.required_capability.value} "
                        f"but exposes it to {mode.value}"
                    )
        if page.mobile_primary:
            mobile_count += 1
    if mobile_count != 3:
        errors.append("Mobile primary navigation must contain exactly three pages")
    return errors


__all__ = (
    "NAVIGATION_GROUP_ORDER",
    "PORTAL_GROUP",
    "PAGE_DEFINITIONS",
    "PageDefinition",
    "PageKind",
    "WORKBENCH_ACCESS_MODES",
    "mobile_navigation_for",
    "navigation_groups_for",
    "navigation_item_tuples_for",
    "page_definition",
    "portal_pages_for",
    "validate_page_catalog",
)
