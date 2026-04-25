"""add agent profile tables

Revision ID: 0004_add_agent_profile_tables
Revises: 0003_add_tenant_scope_to_slack_tables
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_add_agent_profile_tables"
down_revision = "0003_add_tenant_scope_to_slack_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_profiles",
        sa.Column("agent_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("traits_json", sa.Text(), nullable=False),
        sa.Column("calibration_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_agent_profiles_tenant_id", "agent_profiles", ["tenant_id"], unique=False)
    op.create_index("ix_agent_profiles_user_id", "agent_profiles", ["user_id"], unique=False)

    op.create_table(
        "agent_profile_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("traits_json", sa.Text(), nullable=False),
        sa.Column("calibration_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("reason", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_agent_profile_versions_agent_id", "agent_profile_versions", ["agent_id"], unique=False)
    op.create_index("ix_agent_profile_versions_tenant_id", "agent_profile_versions", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agent_profile_versions_tenant_id", table_name="agent_profile_versions")
    op.drop_index("ix_agent_profile_versions_agent_id", table_name="agent_profile_versions")
    op.drop_table("agent_profile_versions")

    op.drop_index("ix_agent_profiles_user_id", table_name="agent_profiles")
    op.drop_index("ix_agent_profiles_tenant_id", table_name="agent_profiles")
    op.drop_table("agent_profiles")
