"""Read-only integrity checks shared by live readiness and isolated recovery."""
import re
import sqlite3

from roster_core.dated_draft import decode_draft, encode_draft
from roster_policy.policy_codec import encode_weekly_policy


DATED_DRAFT_TABLES = frozenset({"dated_draft_revisions", "dated_draft_current"})


def dated_drafts_are_valid(connection: sqlite3.Connection) -> bool:
    try:
        history = {}
        metadata = {}
        for identity, version, year, policy_version, monday, document, policy_document, command_type, command_status in connection.execute(
            "SELECT d.schedule_id,d.version,d.year_start,d.policy_revision,d.week_start,d.document,p.document,c.operation_type,c.status "
            "FROM dated_draft_revisions d LEFT JOIN school_year_policy_revisions p "
            "ON p.year_start=d.year_start AND p.revision=d.policy_revision "
            "LEFT JOIN operation_commands c ON c.command_id=d.command_id ORDER BY d.schedule_id,d.version"
        ):
            if (type(identity) is not str or re.fullmatch(r"DRAFT-[0-9a-f]{32}", identity) is None
                    or type(version) is not int or not 1 <= version <= 2**63 - 1
                    or version != history.get(identity, 0) + 1 or command_status != "committed"
                    or command_type not in {"dated_draft_created", "dated_draft_regenerated", "dated_draft_policy_adopted", "dated_draft_edited"}):
                return False
            draft = decode_draft(document)
            if (encode_draft(draft) != document or draft.policy_ref.year_start != year
                    or draft.policy_ref.revision != policy_version
                    or encode_weekly_policy(draft.policy_ref.policy) != policy_document
                    or draft.schedule.dates[0].isoformat() != monday):
                return False
            if identity in metadata and metadata[identity] != (year, monday):
                return False
            metadata[identity] = (year, monday)
            history[identity] = version
        current = {}
        dates = set()
        for identity, version, monday in connection.execute("SELECT schedule_id,version,week_start FROM dated_draft_current"):
            if identity not in metadata or metadata[identity][1] != monday or monday in dates or type(version) is not int:
                return False
            current[identity] = version
            dates.add(monday)
        return current == history
    except (ValueError, TypeError, sqlite3.Error):
        return False
