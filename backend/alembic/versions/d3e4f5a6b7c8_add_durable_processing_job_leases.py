"""Add durable processing job leases and retry scheduling.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('UPDATE processing_jobs SET attempt_count = 0 WHERE attempt_count IS NULL')
    op.add_column(
        'processing_jobs',
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column('processing_jobs', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('processing_jobs', sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('processing_jobs', sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('processing_jobs', sa.Column('worker_id', sa.String(length=128), nullable=True))
    op.execute(
        "UPDATE processing_jobs SET available_at = COALESCE(created_at, CURRENT_TIMESTAMP) "
        "WHERE status = 'queued' AND available_at IS NULL"
    )
    op.execute(
        "UPDATE processing_jobs SET status = 'queued', "
        "available_at = COALESCE(created_at, CURRENT_TIMESTAMP), "
        "started_at = NULL, "
        "error_category = 'recovered_during_worker_migration' "
        "WHERE status = 'running'"
    )
    op.create_index('ix_processing_jobs_status_available', 'processing_jobs', ['status', 'available_at'])
    op.create_index('ix_processing_jobs_lease_expires_at', 'processing_jobs', ['lease_expires_at'])


def downgrade() -> None:
    op.drop_index('ix_processing_jobs_lease_expires_at', table_name='processing_jobs')
    op.drop_index('ix_processing_jobs_status_available', table_name='processing_jobs')
    op.drop_column('processing_jobs', 'worker_id')
    op.drop_column('processing_jobs', 'lease_expires_at')
    op.drop_column('processing_jobs', 'finished_at')
    op.drop_column('processing_jobs', 'started_at')
    op.drop_column('processing_jobs', 'available_at')
