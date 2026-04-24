"""add tenant scope to slack tables

Revision ID: 0003_add_tenant_scope_to_slack_tables
Revises: 0002_add_slack_queue_tables
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_tenant_scope_to_slack_tables"
down_revision = "0002_add_slack_queue_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "slack_inbound_events",
        sa.Column("tenant_id", sa.String(length=128), nullable=False, server_default="public"),
    )
    op.add_column(
        "slack_sent_dedupes",
        sa.Column("tenant_id", sa.String(length=128), nullable=False, server_default="public"),
    )
    op.add_column(
        "slack_outbound_messages",
        sa.Column("tenant_id", sa.String(length=128), nullable=False, server_default="public"),
    )

    op.create_index("ix_slack_inbound_events_tenant_id", "slack_inbound_events", ["tenant_id"], unique=False)
    op.create_index("ix_slack_sent_dedupes_tenant_id", "slack_sent_dedupes", ["tenant_id"], unique=False)
    op.create_index("ix_slack_outbound_messages_tenant_id", "slack_outbound_messages", ["tenant_id"], unique=False)

    op.drop_index("ix_slack_inbound_events_event_id", table_name="slack_inbound_events")
    op.create_index(
        "ix_slack_inbound_events_tenant_event_id",
        "slack_inbound_events",
        ["tenant_id", "event_id"],
        unique=True,
    )

    op.drop_index("ix_slack_sent_dedupes_dedupe_key", table_name="slack_sent_dedupes")
    op.create_index(
        "ix_slack_sent_dedupes_tenant_dedupe_key",
        "slack_sent_dedupes",
        ["tenant_id", "dedupe_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_slack_sent_dedupes_tenant_dedupe_key", table_name="slack_sent_dedupes")
    op.create_index("ix_slack_sent_dedupes_dedupe_key", "slack_sent_dedupes", ["dedupe_key"], unique=True)

    op.drop_index("ix_slack_inbound_events_tenant_event_id", table_name="slack_inbound_events")
    op.create_index("ix_slack_inbound_events_event_id", "slack_inbound_events", ["event_id"], unique=True)

    op.drop_index("ix_slack_outbound_messages_tenant_id", table_name="slack_outbound_messages")
    op.drop_index("ix_slack_sent_dedupes_tenant_id", table_name="slack_sent_dedupes")
    op.drop_index("ix_slack_inbound_events_tenant_id", table_name="slack_inbound_events")

    op.drop_column("slack_outbound_messages", "tenant_id")
    op.drop_column("slack_sent_dedupes", "tenant_id")
    op.drop_column("slack_inbound_events", "tenant_id")
