"""Add discovery metadata for documents and student preferences.

Revision ID: e7a19c4b8d21
Revises: d1e2f3a4b5c6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7a19c4b8d21'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('grade', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('academic_year', sa.Integer(), nullable=True))
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('preferred_grade', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('preferred_grade')
    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_column('academic_year')
        batch_op.drop_column('grade')
