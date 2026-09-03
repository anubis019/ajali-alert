"""Create the initial operational schema.

Revision ID: 0001_initial_operational_schema
Revises:
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_operational_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_token_hash", "refresh_sessions", ["token_hash"])
    op.create_table(
        "incident_types",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("default_priority", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "responders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("responder_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("incident_number", sa.String(), nullable=False),
        sa.Column("type_id", sa.String(), nullable=True),
        sa.Column("reporter_phone", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("casualty_count", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location_description", sa.String(), nullable=True),
        sa.Column("landmark", sa.String(), nullable=True),
        sa.Column("is_escalated", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["type_id"], ["incident_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_number"),
    )
    op.create_table(
        "incident_status_history",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "dispatch_assignments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=True),
        sa.Column("responder_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("eta_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.ForeignKeyConstraint(["responder_id"], ["responders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_responders_status", "responders", ["status"])


def downgrade() -> None:
    op.drop_index("ix_refresh_sessions_token_hash", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_user_id", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_index("ix_responders_status", table_name="responders")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_created_at", table_name="incidents")
    op.drop_table("dispatch_assignments")
    op.drop_table("incident_status_history")
    op.drop_table("incidents")
    op.drop_table("responders")
    op.drop_table("incident_types")
    op.drop_table("users")
