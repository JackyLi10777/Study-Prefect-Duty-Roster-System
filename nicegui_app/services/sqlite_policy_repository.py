"""Standalone test Adapter using the formal policy tables.

Only the supplied Engine is used. Construction performs no I/O; schema creation
is an explicit isolated-test action, not application bootstrap or a migration.
"""

from __future__ import annotations

from sqlalchemy import (
    Column, ForeignKeyConstraint, Integer, MetaData, String, Table,
    insert, select, text, update,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from nicegui_app.persistence.models import Base, SchoolYearPolicyCurrentRecord, SchoolYearPolicyRevisionRecord

from roster_core.policy_settings import (
    PolicyCommandConflict, PolicyOperation, PolicyStorageError, PolicyVersionConflict, StoredPolicyRevision,
)


_revisions = SchoolYearPolicyRevisionRecord.__table__
_current = SchoolYearPolicyCurrentRecord.__table__
# Only the standalone test Adapter owns this receipt table. Formal commands
# continue to use operation_commands in their caller-owned transaction.
_metadata = MetaData()
_commands = Table(
    "prelaunch_policy_commands", _metadata,
    Column("command_id", String(64), primary_key=True),
    Column("request_digest", String(64), nullable=False),
    Column("year_start", Integer, nullable=False),
    Column("revision", Integer, nullable=False),
    ForeignKeyConstraint(
        ["year_start", "revision"], [_revisions.c.year_start, _revisions.c.revision],
    ),
)


def create_policy_revision_schema(connection: Connection) -> None:
    """Create only the two canonical tables for isolated Adapter tests.

    The caller configures SQLite foreign keys and owns commit/rollback. No
    standalone command table is created. This is not the full formal schema;
    application bootstrap and recovery must use the reviewed Alembic chain.
    """
    Base.metadata.create_all(connection, tables=[_revisions, _current])


def _read_policy_revision(
    connection: Connection, year_start: int, revision: int | None = None,
) -> StoredPolicyRevision | None:
    statement = select(_revisions).where(_revisions.c.year_start == year_start)
    if revision is None:
        statement = statement.join(
            _current,
            (_current.c.year_start == _revisions.c.year_start) & (_current.c.revision == _revisions.c.revision),
        )
    else:
        statement = statement.where(_revisions.c.revision == revision)
    row = connection.execute(statement).mappings().one_or_none()
    return StoredPolicyRevision(row["year_start"], row["revision"], row["document"]) if row else None


def _append_policy_revision(
    connection: Connection, year_start: int, expected_revision: int, document: str,
) -> StoredPolicyRevision:
    """Append under the caller's reserved SQLite writer transaction."""
    current_revision = connection.scalar(select(_current.c.revision).where(_current.c.year_start == year_start))
    if (current_revision or 0) != expected_revision:
        raise PolicyVersionConflict("The current policy changed; reload before saving.")
    new_revision = expected_revision + 1
    connection.execute(insert(_revisions).values(year_start=year_start, revision=new_revision, document=document))
    if current_revision is None:
        connection.execute(insert(_current).values(year_start=year_start, revision=new_revision))
    else:
        connection.execute(update(_current).where(_current.c.year_start == year_start).values(revision=new_revision))
    return StoredPolicyRevision(year_start, new_revision, document)


class SQLitePolicyRepository:
    def __init__(self, engine: Engine) -> None:
        if not isinstance(engine, Engine) or engine.dialect.name != "sqlite":
            raise PolicyStorageError("Policy storage requires an explicitly supplied SQLite Engine.")
        self._engine = engine

    def create_schema(self) -> None:
        """Initialize the isolated test Adapter, never the full application."""
        try:
            with self._engine.connect() as connection:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                create_policy_revision_schema(connection)
                _metadata.create_all(connection)
                connection.commit()
        except SQLAlchemyError as error:
            raise PolicyStorageError("Policy schema initialization failed.") from error

    def read(self, year_start: int, revision: int | None = None) -> StoredPolicyRevision | None:
        try:
            with self._engine.connect() as connection:
                stored = _read_policy_revision(connection, year_start, revision)
            return stored
        except SQLAlchemyError as error:
            raise PolicyStorageError("Policy storage read failed.") from error

    def commit(
        self, year_start: int, expected_revision: int, document: str,
        command_id: str, request_digest: str, *, operation: PolicyOperation,
    ) -> StoredPolicyRevision:
        try:
            with self._engine.connect() as connection:
                # The supplied Engine need not have an application connection
                # hook. SQLite only accepts this pragma outside a transaction.
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                if connection.scalar(text("PRAGMA foreign_keys")) != 1:
                    raise PolicyStorageError("SQLite foreign key enforcement is required for policy writes.")
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                receipt = connection.execute(
                    select(_commands).where(_commands.c.command_id == command_id),
                ).mappings().one_or_none()
                if receipt is not None:
                    if receipt["request_digest"] != request_digest:
                        raise PolicyCommandConflict("This command ID was already used for different policy work.")
                    stored = _read_policy_revision(connection, receipt["year_start"], receipt["revision"])
                    if stored is None:
                        raise PolicyStorageError("The policy receipt refers to a missing revision.")
                    connection.rollback()
                    return stored
                stored = _append_policy_revision(connection, year_start, expected_revision, document)
                connection.execute(insert(_commands).values(
                    command_id=command_id, request_digest=request_digest, year_start=year_start, revision=stored.revision,
                ))
                connection.commit()
                return stored
        except SQLAlchemyError as error:
            raise PolicyStorageError("Policy storage commit failed.") from error
