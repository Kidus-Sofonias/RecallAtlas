import pytest
from fastapi import HTTPException

from app.api.backup import download_backup


def test_backup_export_reports_unimplemented_postgresql_backup():
    with pytest.raises(HTTPException) as error:
        download_backup()

    assert error.value.status_code == 501
