"""Traditional-Chinese-first user-interface messages and display labels."""

from __future__ import annotations

from roster_policy import DutyPost, SchoolDay
from nicegui_app.ui.preferences import preference_get, preference_set


ZH_HK = "zh-HK"
EN = "en"

from nicegui_app.ui.i18n_catalog import MESSAGES


DAY_LABELS = {
    SchoolDay.MONDAY: {ZH_HK: "星期一", EN: "Monday"},
    SchoolDay.TUESDAY: {ZH_HK: "星期二", EN: "Tuesday"},
    SchoolDay.WEDNESDAY: {ZH_HK: "星期三", EN: "Wednesday"},
    SchoolDay.THURSDAY: {ZH_HK: "星期四", EN: "Thursday"},
    SchoolDay.FRIDAY: {ZH_HK: "星期五", EN: "Friday"},
}

POST_LABELS = {
    DutyPost.ASSIST_IN_CHARGE: {ZH_HK: "助理首席導學風紀當值", EN: "Assist. in charge"},
    DutyPost.ROOM_302: {ZH_HK: "302 室", EN: "Room 302"},
    DutyPost.ROOM_303: {ZH_HK: "303 室", EN: "Room 303"},
    DutyPost.ROOM_202: {ZH_HK: "202 室", EN: "Room 202"},
}

OFFICIAL_ROLE_TERMS = {
    "head_study_prefect": {ZH_HK: "首席導學風紀", EN: "Head Study Prefect"},
    "assistant_head_study_prefect": {ZH_HK: "助理首席導學風紀", EN: "Assistant Head Study Prefect"},
    "study_prefect": {ZH_HK: "導學風紀", EN: "Study Prefect"},
}

ROLE_LABELS = {
    "assistant_head": OFFICIAL_ROLE_TERMS["assistant_head_study_prefect"],
    "study_prefect": OFFICIAL_ROLE_TERMS["study_prefect"],
}


def current_locale() -> str:
    return str(preference_get("locale", ZH_HK))


def t(key: str, **values: object) -> str:
    message = _localized(MESSAGES[key])
    return message.format(**values)


def day_label(day: SchoolDay | str) -> str:
    school_day = SchoolDay[day] if isinstance(day, str) else day
    return _localized(DAY_LABELS[school_day])


def post_label(post_code: str) -> str:
    return _localized(POST_LABELS[DutyPost[post_code]])


def role_label(role_code: str) -> str:
    return _localized(ROLE_LABELS[role_code])


def toggle_locale() -> None:
    preference_set("locale", EN if current_locale() == ZH_HK else ZH_HK)


def _localized(messages: dict[str, str]) -> str:
    return messages.get(current_locale(), messages[ZH_HK])
