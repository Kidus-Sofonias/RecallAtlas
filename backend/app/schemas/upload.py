import uuid
from pydantic import BaseModel, Field
from typing import Optional

SUPPORTED_UPLOADS = {
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
    '.tif': 'image/tiff',
    '.tiff': 'image/tiff',
    '.bmp': 'image/bmp',
}

class UploadInitiateRequest(BaseModel):
    filename: str
    mime_type: str
    file_size: int = Field(gt=0)
    no_answers_confirmed: bool = False
    title: Optional[str] = None
    grade: Optional[int] = Field(default=None, ge=9, le=12)
    academic_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    subject_id: Optional[uuid.UUID] = None

    def validate_supported_file(self) -> None:
        from pathlib import PurePath

        extension = PurePath(self.filename).suffix.lower()
        if SUPPORTED_UPLOADS.get(extension) != self.mime_type:
            raise ValueError('Filename extension and supported MIME type must match.')

class UploadInitiateResponse(BaseModel):
    document_id: str
    storage_object_key: str
    upload_url: str
