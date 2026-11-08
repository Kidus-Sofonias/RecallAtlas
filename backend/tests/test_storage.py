import io

import pytest

from app.core.config import settings
from app.storage import files as storage


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body):
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        return {'Body': io.BytesIO(self.objects[(Bucket, Key)])}

    def copy_object(self, CopySource, Bucket, Key):
        self.objects[(Bucket, Key)] = self.objects[
            (CopySource['Bucket'], CopySource['Key'])
        ]

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)


def test_s3_storage_saves_reads_moves_and_deletes_private_objects(monkeypatch):
    client = FakeS3()
    monkeypatch.setattr(settings, 'storage_backend', 's3')
    monkeypatch.setattr(settings, 'object_storage_bucket', 'private-test-bucket')
    monkeypatch.setattr(storage, '_s3_client', lambda: client)

    storage.save_bytes('quarantine/document/source.pdf', b'pdf bytes')
    assert storage.read_bytes('quarantine/document/source.pdf') == b'pdf bytes'
    assert ('private-test-bucket', 'quarantine/document/source.pdf') in client.objects

    storage.move('quarantine/document/source.pdf', 'uploads/document/source.pdf')

    assert storage.read_bytes('uploads/document/source.pdf') == b'pdf bytes'
    assert ('private-test-bucket', 'quarantine/document/source.pdf') not in client.objects
    storage.delete('uploads/document/source.pdf')
    assert ('private-test-bucket', 'uploads/document/source.pdf') not in client.objects


@pytest.mark.parametrize(
    'key',
    ['', '/absolute/source.pdf', '../source.pdf', 'uploads/../source.pdf', r'uploads\source.pdf'],
)
def test_s3_storage_rejects_non_relative_keys(monkeypatch, key):
    monkeypatch.setattr(settings, 'storage_backend', 's3')

    with pytest.raises(ValueError, match='relative object paths'):
        storage.read_bytes(key)
