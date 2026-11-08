"""Add structured extraction metadata to documents and questions.

Revision ID: a1b2c3d4e5f6
Revises: f8b26d3c9e40
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f8b26d3c9e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM collection_items
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY collection_id, question_id
                    ORDER BY created_at, id
                ) AS duplicate_number
                FROM collection_items
            ) ranked
            WHERE duplicate_number > 1
        )
        """
    )
    with op.batch_alter_table('collection_items') as batch_op:
        batch_op.create_unique_constraint(
            'uq_collection_items_collection_question',
            ['collection_id', 'question_id'],
        )

    op.add_column('documents', sa.Column('original_filename', sa.String(length=255), nullable=True))
    op.add_column('documents', sa.Column('no_answers_confirmed', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column('questions', sa.Column('question_type', sa.String(length=32), nullable=False, server_default='unknown'))
    op.add_column('questions', sa.Column('review_status', sa.String(length=16), nullable=False, server_default='pending'))
    op.add_column('questions', sa.Column('content_json', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('quality_signals_json', sa.Text(), nullable=True))
    op.add_column('questions', sa.Column('extraction_version', sa.String(length=32), nullable=True))

    with op.batch_alter_table('comments') as batch_op:
        batch_op.add_column(sa.Column('parent_comment_id', sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            'fk_comments_parent_comment_id_comments',
            'comments',
            ['parent_comment_id'],
            ['id'],
        )
        batch_op.add_column(sa.Column('moderation_status', sa.String(length=16), nullable=False, server_default='published'))

    with op.batch_alter_table('reports') as batch_op:
        batch_op.add_column(sa.Column('details', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('decision', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('reviewed_by', sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('review_notes', sa.Text(), nullable=True))
        batch_op.create_foreign_key('fk_reports_reviewed_by_users', 'users', ['reviewed_by'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('reports') as batch_op:
        batch_op.drop_constraint('fk_reports_reviewed_by_users', type_='foreignkey')
        batch_op.drop_column('review_notes')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('reviewed_by')
        batch_op.drop_column('decision')
        batch_op.drop_column('details')

    with op.batch_alter_table('comments') as batch_op:
        batch_op.drop_column('moderation_status')
        batch_op.drop_constraint('fk_comments_parent_comment_id_comments', type_='foreignkey')
        batch_op.drop_column('parent_comment_id')

    op.drop_column('questions', 'extraction_version')
    op.drop_column('questions', 'quality_signals_json')
    op.drop_column('questions', 'content_json')
    op.drop_column('questions', 'review_status')
    op.drop_column('questions', 'question_type')

    op.drop_column('documents', 'no_answers_confirmed')
    op.drop_column('documents', 'original_filename')

    with op.batch_alter_table('collection_items') as batch_op:
        batch_op.drop_constraint('uq_collection_items_collection_question', type_='unique')
