"""add query indexes and timezone-aware timestamps

Adds indexes for the columns the dashboard filters, sorts, and groups by, and
makes timestamp columns timezone-aware.

The timestamp change is a no-op on SQLite, which has no native timestamp type
and stores datetimes as text either way. On PostgreSQL the columns are altered
to TIMESTAMPTZ; existing values are already UTC, so they are reinterpreted
rather than shifted.

Revision ID: b2c4d81e7a13
Revises: 6f6a66300caf
Create Date: 2026-07-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c4d81e7a13"
down_revision: str | None = "6f6a66300caf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (index name, table, column)
_INDEXES = [
    ("ix_traces_started_at", "traces", "started_at"),
    ("ix_traces_status", "traces", "status"),
    ("ix_spans_started_at", "spans", "started_at"),
    ("ix_spans_event_type", "spans", "event_type"),
    ("ix_spans_model", "spans", "model"),
]

# (table, column, nullable)
_TIMESTAMP_COLUMNS = [
    ("traces", "started_at", False),
    ("traces", "ended_at", True),
    ("spans", "started_at", False),
    ("spans", "ended_at", True),
    ("drift_baselines", "built_at", False),
    ("drift_alerts", "detected_at", False),
    ("drift_rebuild_requests", "requested_at", False),
]


def upgrade() -> None:
    for name, table, column in _INDEXES:
        op.create_index(name, table, [column], unique=False)

    if op.get_bind().dialect.name != "postgresql":
        return
    for table, column, nullable in _TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table, column, nullable in _TIMESTAMP_COLUMNS:
            op.alter_column(
                table,
                column,
                type_=sa.DateTime(),
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=nullable,
            )

    for name, table, _column in _INDEXES:
        op.drop_index(name, table_name=table)
