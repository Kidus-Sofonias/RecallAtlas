"""Add fail-closed upload security scan state.

Revision ID: c2d3e4f5a6b7
Revises: b7c8d9e0f1a2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'documents',
        sa.Column('security_status', sa.String(length=16), nullable=False, server_default='clean'),
    )
    op.add_column('documents', sa.Column('security_scan_detail', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('security_scanned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('documents', sa.Column('security_reviewed_by', sa.Uuid(), nullable=True))
    op.add_column('documents', sa.Column('security_reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('documents', sa.Column('security_review_note', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'security_review_note')
    op.drop_column('documents', 'security_reviewed_at')
    op.drop_column('documents', 'security_reviewed_by')
    op.drop_column('documents', 'security_scanned_at')
    op.drop_column('documents', 'security_scan_detail')
    op.drop_column('documents', 'security_status')
