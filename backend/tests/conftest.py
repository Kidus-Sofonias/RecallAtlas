import os
import sys
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

backend_directory = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_directory))

test_data = tempfile.TemporaryDirectory(prefix='recall-atlas-tests-')
test_directory = Path(test_data.name)
os.environ['APP_ENV'] = 'test'
os.environ['RECALL_STORAGE_PATH'] = str(test_directory / 'storage_private')
os.environ['ADMIN_EMAIL'] = 'test-admin@example.test'
os.environ['ADMIN_INITIAL_PASSWORD'] = 'Test-Only-Admin-Password-2026'
os.environ['EMAIL_DEV_MODE'] = 'true'

test_database_url = os.environ.get('TEST_DATABASE_URL', '').strip()
if not test_database_url:
    raise RuntimeError(
        'TEST_DATABASE_URL must point to a dedicated PostgreSQL database named with "test". '
        'Start the local PostgreSQL service and follow Documentation/postgresql-setup.md.'
    )
parsed_test_url = make_url(test_database_url)
if parsed_test_url.get_backend_name() != 'postgresql':
    raise RuntimeError('TEST_DATABASE_URL must use PostgreSQL; SQLite test databases are not supported.')
if not parsed_test_url.database or 'test' not in parsed_test_url.database.casefold():
    raise RuntimeError('TEST_DATABASE_URL must target a dedicated database with "test" in its name.')

schema_name = f'recall_atlas_test_{uuid.uuid4().hex}'
admin_engine = create_engine(parsed_test_url, pool_pre_ping=True)
with admin_engine.begin() as connection:
    connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

isolated_test_url = parsed_test_url.update_query_dict({
    'options': f'-csearch_path={schema_name}',
})
os.environ['DATABASE_URL'] = isolated_test_url.render_as_string(hide_password=False)

from app.db.session import engine
from alembic import command
from alembic.config import Config
from app.db.session import SessionLocal
from app.services.auth import bootstrap_admin

alembic_config = Config(str(backend_directory.parent / 'alembic.ini'))
alembic_config.set_main_option('script_location', str(backend_directory / 'alembic'))
command.upgrade(alembic_config, 'head')
with SessionLocal() as db:
    bootstrap_admin(db, os.environ['ADMIN_EMAIL'], os.environ['ADMIN_INITIAL_PASSWORD'])


def pytest_unconfigure(config):
    engine.dispose()
    with admin_engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
    admin_engine.dispose()
    test_data.cleanup()


def pytest_runtest_setup(item):
    from app.middleware import _buckets

    _buckets.clear()
