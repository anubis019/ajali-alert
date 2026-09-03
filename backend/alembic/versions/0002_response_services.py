"""Add response coordination entities and spatial columns.

Revision ID: 0002_response_services
Revises: 0001_initial_operational_schema
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision: str = "0002_response_services"
down_revision: Union[str, None] = "0001_initial_operational_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    location_type = Geometry("POINT", srid=4326) if is_postgres else sa.String()

    op.add_column("incidents", sa.Column("location", location_type, nullable=True))
    op.add_column("responders", sa.Column("location", location_type, nullable=True))
    op.add_column("responders", sa.Column("last_location_at", sa.DateTime(), nullable=True))
    if is_postgres:
        op.create_index("ix_incidents_location_gist", "incidents", ["location"], postgresql_using="gist")
        op.create_index("ix_responders_location_gist", "responders", ["location"], postgresql_using="gist")

    op.create_table(
        "hospitals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location", location_type, nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("emergency_available", sa.Boolean(), nullable=False),
        sa.Column("available_beds", sa.Integer(), nullable=False),
        sa.Column("trauma_capable", sa.Boolean(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    if is_postgres:
        op.create_index("ix_hospitals_location_gist", "hospitals", ["location"], postgresql_using="gist")
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=True),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ussd_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_ussd_sessions_session_id", "ussd_sessions", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_ussd_sessions_session_id", table_name="ussd_sessions")
    op.drop_table("ussd_sessions")
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_hospitals_location_gist", table_name="hospitals")
    op.drop_table("hospitals")
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_responders_location_gist", table_name="responders")
        op.drop_index("ix_incidents_location_gist", table_name="incidents")
    op.drop_column("responders", "last_location_at")
    op.drop_column("responders", "location")
    op.drop_column("incidents", "location")
