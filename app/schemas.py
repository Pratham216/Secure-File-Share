from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_verified: bool
    is_ops_user: bool
    created_at: datetime

    class Config:
        orm_mode = True

class UserVerify(BaseModel):
    token: str

class FileBase(BaseModel):
    filename: str

class FileCreate(FileBase):
    pass

class File(FileBase):
    id: int
    file_type: str
    uploaded_by: int
    uploaded_at: datetime

    class Config:
        orm_mode = True

class DownloadTokenCreate(BaseModel):
    file_id: int

class DownloadTokenResponse(BaseModel):
    download_url: str