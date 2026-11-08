import secrets

from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = 'postgresql+psycopg2://recall_atlas:local-dev-only@127.0.0.1:5432/recall_atlas'
    app_env: str = 'production'
    storage_backend: str = 'local'
    object_storage_bucket: str = ''
    object_storage_region: str = 'us-east-1'
    object_storage_endpoint_url: str = ''
    object_storage_access_key_id: str = ''
    object_storage_secret_access_key: str = ''
    secret_key: str = Field(default_factory=lambda: f'dev-ephemeral-{secrets.token_urlsafe(48)}')
    resend_api_key: str = ''
    resend_from_email: str = 'onboarding@resend.dev'
    email_dev_mode: bool = True
    frontend_url: str = 'http://127.0.0.1:5173'
    admin_email: str = ''
    admin_initial_password: str = ''
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)
    clamd_host: str = ''
    clamd_port: int = Field(default=3310, ge=1, le=65535)
    clamd_timeout_seconds: float = Field(default=5, gt=0, le=30)
    processing_max_attempts: int = Field(default=3, ge=1, le=10)
    processing_retry_base_seconds: int = Field(default=30, ge=1, le=3600)
    processing_lease_seconds: int = Field(default=1800, ge=60, le=86400)
    processing_worker_poll_seconds: float = Field(default=2, gt=0, le=60)

    class Config:
        env_file = '.env'
        extra = 'ignore'

settings = Settings()


def ensure_authentication_ready(
    app_env: str,
    secret_key: str = '',
    admin_email: str = '',
    admin_initial_password: str = '',
) -> None:
    if bool(admin_email) != bool(admin_initial_password):
        raise RuntimeError('ADMIN_EMAIL and ADMIN_INITIAL_PASSWORD must be configured together.')
    if app_env.lower() in {'development', 'test'}:
        return
    if len(secret_key) < 32 or secret_key.startswith('dev-ephemeral-'):
        raise RuntimeError('SECRET_KEY must contain at least 32 characters outside development/test.')


def ensure_deployment_ready(
    app_env: str,
    database_url: str,
    storage_backend: str,
    object_storage_bucket: str = '',
) -> None:
    if not database_url.lower().startswith(('postgresql://', 'postgresql+psycopg2://')):
        raise RuntimeError('PostgreSQL must be configured in every environment.')
    if app_env.lower() in {'development', 'test'}:
        return
    if storage_backend.lower() != 's3':
        raise RuntimeError('S3-compatible durable object storage must be configured outside development/test.')
    if not object_storage_bucket.strip():
        raise RuntimeError('OBJECT_STORAGE_BUCKET must be configured when STORAGE_BACKEND=s3.')
