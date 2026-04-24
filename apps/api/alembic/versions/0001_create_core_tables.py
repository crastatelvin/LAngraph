"""create core tables

Revision ID: 0001_create_core_tables
Revises: 
Create Date: 2026-04-24
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_create_core_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "debates",
        sa.Column("debate_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("proposal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_debates_tenant_id", "debates", ["tenant_id"])

    op.create_table(
        "debate_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("debate_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_debate_events_debate_id", "debate_events", ["debate_id"])
    op.create_index("ix_debate_events_tenant_id", "debate_events", ["tenant_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource", sa.String(length=256), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_tenant_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_debate_events_tenant_id", table_name="debate_events")
    op.drop_index("ix_debate_events_debate_id", table_name="debate_events")
    op.drop_table("debate_events")

    op.drop_index("ix_debates_tenant_id", table_name="debates")
    op.drop_table("debates")
