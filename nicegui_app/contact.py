"""Non-sensitive project feedback contact shared by the NiceGUI presentation layer."""

from __future__ import annotations

from urllib.parse import urlencode


FEEDBACK_EMAIL = "s10777@syss.edu.hk"
FEEDBACK_SUBJECT = "Sing Yin Roster feedback / 導學風紀值班系統反饋"
FEEDBACK_MAILTO_URL = f"mailto:{FEEDBACK_EMAIL}?{urlencode({'subject': FEEDBACK_SUBJECT})}"
GITHUB_REPOSITORY_URL = "https://github.com/JackyLi10777/Study-Prefect-Duty-Roster-System"
