import secrets
from datetime import datetime, timedelta
from . import models, schemas
from .config import settings
import os
from fastapi import HTTPException, status

ALLOWED_EXTENSIONS = {'pptx', 'docx', 'xlsx'}

def generate_download_token():
    return secrets.token_urlsafe(32)

def save_uploaded_file(file, user_id: int):
    # Check file extension
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Create directory if not exists
    os.makedirs("static/files", exist_ok=True)
    
    # Generate unique filename
    unique_filename = f"{user_id}_{secrets.token_hex(8)}.{file_extension}"
    file_path = f"static/files/{unique_filename}"
    
    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
    
    return {
        "filename": file.filename,
        "filepath": file_path,
        "file_type": file_extension
    }