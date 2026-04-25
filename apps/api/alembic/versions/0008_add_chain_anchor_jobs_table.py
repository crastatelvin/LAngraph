"""add chain anchor jobs table

Revision ID: 0008_add_chain_anchor_jobs_table
Revises: 0007_add_agent_outcomes_table
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008_add_chain_anchor_jobs_table"
down_revision = "0007_add_agent_outcomes_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chain_anchor_jobs",
        sa.Column("job_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("debate_id", sa.String(length=64), nullable=False),
        sa.Column("report_hash", sa.String(length=128), nullable=False),
        sa.Column("network", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tx_hash", sa.String(length=128), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_chain_anchor_jobs_tenant_id", "chain_anchor_jobs", ["tenant_id"], unique=False)
    op.create_index("ix_chain_anchor_jobs_debate_id", "chain_anchor_jobs", ["debate_id"], unique=False)
    op.create_index("ix_chain_anchor_jobs_report_hash", "chain_anchor_jobs", ["report_hash"], unique=False)
    op.create_index("ix_chain_anchor_jobs_status", "chain_anchor_jobs", ["status"], unique=False)
    op.create_index("ix_chain_anchor_jobs_tx_hash", "chain_anchor_jobs", ["tx_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chain_anchor_jobs_tx_hash", table_name="chain_anchor_jobs")
    op.drop_index("ix_chain_anchor_jobs_status", table_name="chain_anchor_jobs")
    op.drop_index("ix_chain_anchor_jobs_report_hash", table_name="chain_anchor_jobs")
    op.drop_index("ix_chain_anchor_jobs_debate_id", table_name="chain_anchor_jobs")
    op.drop_index("ix_chain_anchor_jobs_tenant_id", table_name="chain_anchor_jobs")
    op.drop_table("chain_anchor_jobs")
