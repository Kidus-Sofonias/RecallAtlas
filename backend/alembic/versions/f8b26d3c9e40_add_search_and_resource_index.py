"""Add subject interests, article resources, and search index.

Revision ID: f8b26d3c9e40
Revises: e7a19c4b8d21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f8b26d3c9e40'
down_revision: Union[str, None] = 'e7a19c4b8d21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_sqlite_search_index() -> None:
    op.execute(
        """
        CREATE VIRTUAL TABLE content_search USING fts5(
            item_type UNINDEXED,
            item_id UNINDEXED,
            document_id UNINDEXED,
            title,
            body,
            subject,
            grade,
            academic_year,
            tokenize='unicode61 remove_diacritics 2'
        )
        """
    )
    op.execute(
        """
        CREATE TRIGGER content_search_question_insert AFTER INSERT ON questions BEGIN
            INSERT INTO content_search
            SELECT 'question', CAST(q.id AS TEXT), CAST(d.id AS TEXT),
                COALESCE(d.title, ''), q.extracted_text, COALESCE(s.name, ''),
                COALESCE(CAST(d.grade AS TEXT), ''), COALESCE(CAST(d.academic_year AS TEXT), '')
            FROM questions q
            JOIN documents d ON d.id = q.document_id
            LEFT JOIN subjects s ON s.id = d.subject_id
            WHERE q.id = NEW.id
                AND q.quality_status = 'reliable'
                AND d.processing_status = 'completed';
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER content_search_question_update AFTER UPDATE ON questions BEGIN
            DELETE FROM content_search WHERE item_type = 'question' AND item_id = CAST(OLD.id AS TEXT);
            INSERT INTO content_search
            SELECT 'question', CAST(q.id AS TEXT), CAST(d.id AS TEXT),
                COALESCE(d.title, ''), q.extracted_text, COALESCE(s.name, ''),
                COALESCE(CAST(d.grade AS TEXT), ''), COALESCE(CAST(d.academic_year AS TEXT), '')
            FROM questions q
            JOIN documents d ON d.id = q.document_id
            LEFT JOIN subjects s ON s.id = d.subject_id
            WHERE q.id = NEW.id
                AND q.quality_status = 'reliable'
                AND d.processing_status = 'completed';
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER content_search_question_delete AFTER DELETE ON questions BEGIN
            DELETE FROM content_search WHERE item_type = 'question' AND item_id = CAST(OLD.id AS TEXT);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER content_search_document_update AFTER UPDATE ON documents BEGIN
            DELETE FROM content_search WHERE document_id = CAST(OLD.id AS TEXT);
            INSERT INTO content_search
            SELECT 'question', CAST(q.id AS TEXT), CAST(d.id AS TEXT),
                COALESCE(d.title, ''), q.extracted_text, COALESCE(s.name, ''),
                COALESCE(CAST(d.grade AS TEXT), ''), COALESCE(CAST(d.academic_year AS TEXT), '')
            FROM questions q
            JOIN documents d ON d.id = q.document_id
            LEFT JOIN subjects s ON s.id = d.subject_id
            WHERE d.id = NEW.id
                AND q.quality_status = 'reliable'
                AND d.processing_status = 'completed';
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER content_search_subject_update AFTER UPDATE ON subjects BEGIN
            DELETE FROM content_search WHERE document_id IN (
                SELECT CAST(id AS TEXT) FROM documents WHERE subject_id = OLD.id
            );
            INSERT INTO content_search
            SELECT 'question', CAST(q.id AS TEXT), CAST(d.id AS TEXT),
                COALESCE(d.title, ''), q.extracted_text, COALESCE(s.name, ''),
                COALESCE(CAST(d.grade AS TEXT), ''), COALESCE(CAST(d.academic_year AS TEXT), '')
            FROM questions q
            JOIN documents d ON d.id = q.document_id
            LEFT JOIN subjects s ON s.id = d.subject_id
            WHERE d.subject_id = NEW.id
                AND q.quality_status = 'reliable'
                AND d.processing_status = 'completed';
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER content_search_resource_insert AFTER INSERT ON resources
        WHEN NEW.status = 'published' BEGIN
            INSERT INTO content_search
            SELECT 'article', CAST(NEW.id AS TEXT), '',
                NEW.title, NEW.summary || ' ' || NEW.body, COALESCE(s.name, ''), '', ''
            FROM (SELECT 1) AS one
            LEFT JOIN subjects s ON s.id = NEW.subject_id;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER content_search_resource_update AFTER UPDATE ON resources BEGIN
            DELETE FROM content_search WHERE item_type = 'article' AND item_id = CAST(OLD.id AS TEXT);
            INSERT INTO content_search
            SELECT 'article', CAST(NEW.id AS TEXT), '',
                NEW.title, NEW.summary || ' ' || NEW.body, COALESCE(s.name, ''), '', ''
            FROM (SELECT 1) AS one
            LEFT JOIN subjects s ON s.id = NEW.subject_id
            WHERE NEW.status = 'published';
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER content_search_resource_delete AFTER DELETE ON resources BEGIN
            DELETE FROM content_search WHERE item_type = 'article' AND item_id = CAST(OLD.id AS TEXT);
        END
        """
    )


def upgrade() -> None:
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('subject_id', sa.UUID(), nullable=True))
        batch_op.create_foreign_key('fk_documents_subject_id_subjects', 'subjects', ['subject_id'], ['id'])
        batch_op.create_index('ix_documents_subject_id', ['subject_id'])

    op.create_table(
        'user_subject_preferences',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'subject_id'),
    )
    op.create_table(
        'resources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('summary', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('resource_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_resources_subject_id', 'resources', ['subject_id'])

    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        _create_sqlite_search_index()
        op.execute(
            """
            INSERT INTO content_search
            SELECT 'question', CAST(q.id AS TEXT), CAST(d.id AS TEXT),
                COALESCE(d.title, ''), q.extracted_text, COALESCE(s.name, ''),
                COALESCE(CAST(d.grade AS TEXT), ''), COALESCE(CAST(d.academic_year AS TEXT), '')
            FROM questions q
            JOIN documents d ON d.id = q.document_id
            LEFT JOIN subjects s ON s.id = d.subject_id
            WHERE q.quality_status = 'reliable' AND d.processing_status = 'completed'
            """
        )
    elif bind.dialect.name == 'postgresql':
        op.execute(
            "CREATE INDEX ix_questions_search_vector ON questions USING GIN "
            "(to_tsvector('simple', coalesce(extracted_text, '')))"
        )
        op.execute(
            "CREATE INDEX ix_documents_search_vector ON documents USING GIN "
            "(to_tsvector('simple', coalesce(title, '')))"
        )
        op.execute(
            "CREATE INDEX ix_resources_search_vector ON resources USING GIN "
            "(to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(summary, '') || ' ' || coalesce(body, '')))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        for trigger in (
            'content_search_resource_delete',
            'content_search_resource_update',
            'content_search_resource_insert',
            'content_search_subject_update',
            'content_search_document_update',
            'content_search_question_delete',
            'content_search_question_update',
            'content_search_question_insert',
        ):
            op.execute(f'DROP TRIGGER IF EXISTS {trigger}')
        op.execute('DROP TABLE IF EXISTS content_search')
    elif bind.dialect.name == 'postgresql':
        op.execute('DROP INDEX IF EXISTS ix_resources_search_vector')
        op.execute('DROP INDEX IF EXISTS ix_documents_search_vector')
        op.execute('DROP INDEX IF EXISTS ix_questions_search_vector')

    op.drop_index('ix_resources_subject_id', table_name='resources')
    op.drop_table('resources')
    op.drop_table('user_subject_preferences')
    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_index('ix_documents_subject_id')
        batch_op.drop_constraint('fk_documents_subject_id_subjects', type_='foreignkey')
        batch_op.drop_column('subject_id')
