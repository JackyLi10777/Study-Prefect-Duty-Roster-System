"""Add formal school-year policy history without importing rehearsal settings."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "school_year_policy_revisions",
        sa.Column("year_start", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("document", sa.Text(), nullable=False),
        sa.CheckConstraint("typeof(year_start) = 'integer' AND year_start BETWEEN 1 AND 9998", name="ck_policy_revision_year"),
        sa.CheckConstraint("typeof(revision) = 'integer' AND revision BETWEEN 1 AND 9223372036854775807", name="ck_policy_revision_number"),
        sa.PrimaryKeyConstraint("year_start", "revision"),
    )
    op.create_table(
        "school_year_policy_current",
        sa.Column("year_start", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["year_start", "revision"],
            ["school_year_policy_revisions.year_start", "school_year_policy_revisions.revision"],
            name="fk_policy_current_revision",
        ),
        sa.PrimaryKeyConstraint("year_start"),
    )


def downgrade() -> None:
    op.drop_table("school_year_policy_current")
    op.drop_table("school_year_policy_revisions")
