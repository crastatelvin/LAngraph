"""add agent outcomes table

Revision ID: 0007_add_agent_outcomes_table
Revises: 0006_add_chain_anchor_table
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007_add_agent_outcomes_table"
down_revision = "0006_add_chain_anchor_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("debate_id", sa.String(length=64), nullable=False),
        sa.Column("outcome_score", sa.Float(), nullable=False),
        sa.Column("predicted_confidence", sa.Float(), nullable=False),
        sa.Column("actual_score", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_agent_outcomes_agent_id", "agent_outcomes", ["agent_id"], unique=False)
    op.create_index("ix_agent_outcomes_tenant_id", "agent_outcomes", ["tenant_id"], unique=False)
    op.create_index("ix_agent_outcomes_debate_id", "agent_outcomes", ["debate_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_outcomes_debate_id", table_name="agent_outcomes")
    op.drop_index("ix_agent_outcomes_tenant_id", table_name="agent_outcomes")
    op.drop_index("ix_agent_outcomes_agent_id", table_name="agent_outcomes")
    op.drop_table("agent_outcomes")
