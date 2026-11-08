import pytest
from app.core.config import ensure_authentication_ready, ensure_deployment_ready


@pytest.mark.parametrize('app_env', ['production', 'staging'])
def test_api_refuses_nonlocal_environment_without_strong_secret(app_env):
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        ensure_authentication_ready(app_env, 'short-secret')


def test_nonlocal_environment_rejects_ephemeral_development_secret():
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        ensure_authentication_ready('production', 'dev-ephemeral-random-development-value')


def test_nonlocal_environment_accepts_strong_secret_and_admin_configuration():
    ensure_authentication_ready(
        'production',
        'a-long-random-production-secret-that-is-at-least-32-characters',
        'admin@example.test',
        'A-Strong-Initial-Password-2026',
    )


def test_nonlocal_environment_rejects_partial_admin_configuration():
    with pytest.raises(RuntimeError, match='must be configured together'):
        ensure_authentication_ready(
            'production',
            'a-long-random-production-secret-that-is-at-least-32-characters',
            'admin@example.test',
            '',
        )


def test_local_environment_rejects_partial_admin_configuration():
    with pytest.raises(RuntimeError, match='must be configured together'):
        ensure_authentication_ready('development', '', 'admin@example.test', '')


@pytest.mark.parametrize('app_env', ['development', 'test', 'staging', 'production'])
def test_every_environment_requires_postgresql(app_env):
    with pytest.raises(RuntimeError, match='PostgreSQL'):
        ensure_deployment_ready(app_env, 'sqlite:///./dev.db', 'local')


def test_nonlocal_environment_requires_durable_object_storage():
    with pytest.raises(RuntimeError, match='S3-compatible'):
        ensure_deployment_ready('production', 'postgresql://db/app', 'local', '')
    with pytest.raises(RuntimeError, match='OBJECT_STORAGE_BUCKET'):
        ensure_deployment_ready('production', 'postgresql://db/app', 's3', '')


def test_nonlocal_environment_accepts_postgresql_and_s3_storage():
    ensure_deployment_ready('production', 'postgresql+psycopg2://db/app', 's3', 'private-files')


def test_local_environment_accepts_postgresql_and_local_storage():
    ensure_deployment_ready(
        'development',
        'postgresql+psycopg2://db/app',
        'local',
    )


def test_worker_is_executable_as_a_package():
    import importlib.util

    spec = importlib.util.find_spec('app.worker.__main__')

    assert spec is not None
    assert spec.origin is not None
    assert spec.origin.endswith('__main__.py')
