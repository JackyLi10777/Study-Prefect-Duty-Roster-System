"""Own dated draft history without copying rehearsal roster records."""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("dated_draft_revisions",
                    sa.Column("schedule_id", sa.String(38), nullable=False),
                    sa.Column("version", sa.Integer(), nullable=False),
                    sa.Column("year_start", sa.Integer(), nullable=False),
                    sa.Column("policy_revision", sa.Integer(), nullable=False),
                    sa.Column("week_start", sa.Date(), nullable=False),
                    sa.Column("document", sa.Text(), nullable=False),
                    sa.Column("command_id", sa.String(64), nullable=False),
                    sa.ForeignKeyConstraint(["command_id"], ["operation_commands.command_id"]),
                    sa.UniqueConstraint("command_id"),
                    sa.PrimaryKeyConstraint("schedule_id", "version"),
                    sa.CheckConstraint("typeof(version) = 'integer' AND version BETWEEN 1 AND 9223372036854775807", name="ck_dated_draft_version"),
                    sa.ForeignKeyConstraint(["year_start", "policy_revision"],
                                            ["school_year_policy_revisions.year_start", "school_year_policy_revisions.revision"], name="fk_dated_draft_policy"))
    op.create_table("dated_draft_current",
                    sa.Column("schedule_id", sa.String(38), nullable=False),
                    sa.Column("version", sa.Integer(), nullable=False),
                    sa.Column("week_start", sa.Date(), nullable=False),
                    sa.PrimaryKeyConstraint("schedule_id"),
                    sa.UniqueConstraint("week_start", name="uq_dated_draft_week"),
                    sa.ForeignKeyConstraint(["schedule_id", "version"], ["dated_draft_revisions.schedule_id", "dated_draft_revisions.version"], name="fk_dated_draft_current"))


def downgrade():
    op.drop_table("dated_draft_current")
    op.drop_table("dated_draft_revisions")
