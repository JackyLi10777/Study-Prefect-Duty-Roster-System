"""Domain-grouped bilingual user-interface catalogue."""

from nicegui_app.ui.i18n_catalog.foundation import MESSAGES as FOUNDATION_MESSAGES
from nicegui_app.ui.i18n_catalog.weekly import MESSAGES as WEEKLY_MESSAGES
from nicegui_app.ui.i18n_catalog.people import MESSAGES as PEOPLE_MESSAGES
from nicegui_app.ui.i18n_catalog.stewardship import MESSAGES as STEWARDSHIP_MESSAGES
from nicegui_app.ui.i18n_catalog.platform import MESSAGES as PLATFORM_MESSAGES
from nicegui_app.ui.i18n_catalog.media import MESSAGES as MEDIA_MESSAGES
from nicegui_app.ui.i18n_catalog.reporting import MESSAGES as REPORTING_MESSAGES
from nicegui_app.ui.i18n_catalog.importing import MESSAGES as IMPORTING_MESSAGES
from nicegui_app.ui.i18n_catalog.sharing import MESSAGES as SHARING_MESSAGES

MESSAGES: dict[str, dict[str, str]] = {
    **FOUNDATION_MESSAGES,
    **WEEKLY_MESSAGES,
    **PEOPLE_MESSAGES,
    **STEWARDSHIP_MESSAGES,
    **PLATFORM_MESSAGES,
    **MEDIA_MESSAGES,
    **REPORTING_MESSAGES,
    **IMPORTING_MESSAGES,
    **SHARING_MESSAGES,
}
