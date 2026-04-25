"""add federation tables

Revision ID: 0005_add_federation_tables
Revises: 0004_add_agent_profile_tables
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_add_federation_tables"
down_revision = "0004_add_agent_profile_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "federations",
        sa.Column("federation_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_federations_tenant_id", "federations", ["tenant_id"], unique=False)

    op.create_table(
        "federation_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("federation_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_federation_sessions_federation_id", "federation_sessions", ["federation_id"], unique=False)
    op.create_index("ix_federation_sessions_tenant_id", "federation_sessions", ["tenant_id"], unique=False)

    op.create_table(
        "federation_session_submissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("parliament_name", sa.String(length=128), nullable=False),
        sa.Column("position", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("submitted_by", sa.String(length=128), nullable=False),
        sa.Column("submitted_at", sa.String(length=64), nullable=False),
    )
    op.create_index(
        "ix_federation_session_submissions_session_id",
        "federation_session_submissions",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_federation_session_submissions_tenant_id",
        "federation_session_submissions",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_federation_session_submissions_tenant_id", table_name="federation_session_submissions")
    op.drop_index("ix_federation_session_submissions_session_id", table_name="federation_session_submissions")
    op.drop_table("federation_session_submissions")

    op.drop_index("ix_federation_sessions_tenant_id", table_name="federation_sessions")
    op.drop_index("ix_federation_sessions_federation_id", table_name="federation_sessions")
    op.drop_table("federation_sessions")

    op.drop_index("ix_federations_tenant_id", table_name="federations")
    op.drop_table("federations")
