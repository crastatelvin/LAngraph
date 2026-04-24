"""add slack queue tables

Revision ID: 0002_add_slack_queue_tables
Revises: 0001_create_core_tables
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_slack_queue_tables"
down_revision = "0001_create_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slack_inbound_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("seen_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_slack_inbound_events_event_id", "slack_inbound_events", ["event_id"], unique=True)

    op.create_table(
        "slack_sent_dedupes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dedupe_key", sa.String(length=256), nullable=False),
        sa.Column("sent_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_slack_sent_dedupes_dedupe_key", "slack_sent_dedupes", ["dedupe_key"], unique=True)

    op.create_table(
        "slack_outbound_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel", sa.String(length=128), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("thread_ts", sa.String(length=64), nullable=True),
        sa.Column("dedupe_key", sa.String(length=256), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_slack_outbound_messages_channel", "slack_outbound_messages", ["channel"])
    op.create_index("ix_slack_outbound_messages_dedupe_key", "slack_outbound_messages", ["dedupe_key"])
    op.create_index("ix_slack_outbound_messages_status", "slack_outbound_messages", ["status"])


def downgrade() -> None:
    op.drop_index("ix_slack_outbound_messages_status", table_name="slack_outbound_messages")
    op.drop_index("ix_slack_outbound_messages_dedupe_key", table_name="slack_outbound_messages")
    op.drop_index("ix_slack_outbound_messages_channel", table_name="slack_outbound_messages")
    op.drop_table("slack_outbound_messages")

    op.drop_index("ix_slack_sent_dedupes_dedupe_key", table_name="slack_sent_dedupes")
    op.drop_table("slack_sent_dedupes")

    op.drop_index("ix_slack_inbound_events_event_id", table_name="slack_inbound_events")
    op.drop_table("slack_inbound_events")
