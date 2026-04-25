"""add chain anchor table

Revision ID: 0006_add_chain_anchor_table
Revises: 0005_add_federation_tables
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_add_chain_anchor_table"
down_revision = "0005_add_federation_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chain_anchors",
        sa.Column("anchor_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("debate_id", sa.String(length=64), nullable=False),
        sa.Column("report_hash", sa.String(length=128), nullable=False),
        sa.Column("tx_hash", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("network", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("submitted_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_chain_anchors_tenant_id", "chain_anchors", ["tenant_id"], unique=False)
    op.create_index("ix_chain_anchors_debate_id", "chain_anchors", ["debate_id"], unique=False)
    op.create_index("ix_chain_anchors_report_hash", "chain_anchors", ["report_hash"], unique=False)
    op.create_index("ix_chain_anchors_tx_hash", "chain_anchors", ["tx_hash"], unique=True)
    op.create_index("ix_chain_anchors_status", "chain_anchors", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chain_anchors_status", table_name="chain_anchors")
    op.drop_index("ix_chain_anchors_tx_hash", table_name="chain_anchors")
    op.drop_index("ix_chain_anchors_report_hash", table_name="chain_anchors")
    op.drop_index("ix_chain_anchors_debate_id", table_name="chain_anchors")
    op.drop_index("ix_chain_anchors_tenant_id", table_name="chain_anchors")
    op.drop_table("chain_anchors")
