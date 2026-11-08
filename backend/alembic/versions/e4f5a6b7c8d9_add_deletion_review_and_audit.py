"""Add deletion request review lifecycle and audit records.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('deletion_request_status', sa.String(length=16), nullable=False, server_default='none'),
    )
    op.add_column('users', sa.Column('deletion_reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('deletion_reviewed_by', sa.Uuid(), nullable=True))
    op.add_column('users', sa.Column('deletion_review_note', sa.Text(), nullable=True))
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('target_type', sa.String(length=64), nullable=False),
        sa.Column('target_id', sa.String(length=64), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_events_created_at', 'audit_events', ['created_at'])
    op.create_index('ix_audit_events_target', 'audit_events', ['target_type', 'target_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_events_target', table_name='audit_events')
    op.drop_index('ix_audit_events_created_at', table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_column('users', 'deletion_review_note')
    op.drop_column('users', 'deletion_reviewed_by')
    op.drop_column('users', 'deletion_reviewed_at')
    op.drop_column('users', 'deletion_request_status')
