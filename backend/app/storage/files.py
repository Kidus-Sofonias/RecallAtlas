import os
import hashlib
import importlib
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

BASE = Path(os.getenv('RECALL_STORAGE_PATH', 'storage_private'))


def _local_path(key: str) -> Path:
    if not key or Path(key).is_absolute():
        raise ValueError('Storage keys must be relative paths.')
    path = (BASE / key).resolve()
    if not path.is_relative_to(BASE.resolve()):
        raise ValueError('Storage key escapes the private storage directory.')
    return path


def _object_key(key: str) -> str:
    if not key or key.startswith('/') or '\\' in key or '..' in key.split('/'):
        raise ValueError('Storage keys must be relative object paths.')
    return key


@lru_cache(maxsize=1)
def _s3_client():
    try:
        boto3 = importlib.import_module('boto3')
    except ModuleNotFoundError as exc:
        raise RuntimeError('S3 storage requires boto3; install the backend requirements.') from exc

    return boto3.client(
        's3',
        region_name=settings.object_storage_region,
        endpoint_url=settings.object_storage_endpoint_url or None,
        aws_access_key_id=settings.object_storage_access_key_id or None,
        aws_secret_access_key=settings.object_storage_secret_access_key or None,
    )


def save_bytes(key: str, data: bytes) -> str:
    if settings.storage_backend.lower() == 's3':
        object_key = _object_key(key)
        _s3_client().put_object(
            Bucket=settings.object_storage_bucket,
            Key=object_key,
            Body=data,
        )
        return key
    p = _local_path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    temporary = p.with_name(f'.{p.name}.{os.urandom(8).hex()}.tmp')
    try:
        temporary.write_bytes(data)
        temporary.replace(p)
    finally:
        temporary.unlink(missing_ok=True)
    return key

def read_bytes(key: str) -> bytes:
    if settings.storage_backend.lower() == 's3':
        object_key = _object_key(key)
        response = _s3_client().get_object(
            Bucket=settings.object_storage_bucket,
            Key=object_key,
        )
        return response['Body'].read()
    return _local_path(key).read_bytes()


def move(source_key: str, destination_key: str) -> str:
    if settings.storage_backend.lower() == 's3':
        source = _object_key(source_key)
        destination = _object_key(destination_key)
        client = _s3_client()
        client.copy_object(
            CopySource={'Bucket': settings.object_storage_bucket, 'Key': source},
            Bucket=settings.object_storage_bucket,
            Key=destination,
        )
        client.delete_object(
            Bucket=settings.object_storage_bucket,
            Key=source,
        )
        return destination_key
    source = _local_path(source_key)
    destination = _local_path(destination_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.replace(destination)
    return destination_key

def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def delete(key: str):
    if settings.storage_backend.lower() == 's3':
        object_key = _object_key(key)
        _s3_client().delete_object(
            Bucket=settings.object_storage_bucket,
            Key=object_key,
        )
        return
    p = _local_path(key)
    if p.exists(): p.unlink()
