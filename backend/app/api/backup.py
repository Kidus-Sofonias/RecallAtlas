from fastapi import APIRouter, Depends, HTTPException
from app.models.user import User
from app.services.auth import require_admin

router = APIRouter(prefix='/api/v1/admin/backup', tags=['backup'])

@router.get('/download')
def download_backup(admin: User = Depends(require_admin)):
    raise HTTPException(
        status_code=501,
        detail=(
            'PostgreSQL backup export is not implemented. Use a configured '
            'database backup and private-file backup process.'
        ),
    )
