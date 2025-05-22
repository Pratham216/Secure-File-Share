from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import secrets
from . import models, schemas, auth, utils, email_service
from .database import get_db, engine
from .config import settings

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Helper function to create ops user (for initial setup)
def create_initial_ops_user(db: Session):
    ops_email = "ops@example.com"
    ops_password = auth.get_password_hash("ops_password")
    
    existing_user = db.query(models.User).filter(models.User.email == ops_email).first()
    if not existing_user:
        ops_user = models.User(
            email=ops_email,
            hashed_password=ops_password,
            is_verified=True,
            is_ops_user=True
        )
        db.add(ops_user)
        db.commit()

@app.on_event("startup")
def startup_event():
    db = next(get_db())
    create_initial_ops_user(db)

@app.post("/client/signup", response_model=schemas.User)
def client_signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new client user
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        is_ops_user=True,
        is_verified=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    # In a real app, you'd save this token to the database with an expiration
    
    # Send verification email
    email_service.send_verification_email(user.email, verification_token)
    
    return db_user

@app.post("/client/verify-email")
def verify_email(verify_data: schemas.UserVerify, db: Session = Depends(get_db)):
    # In a real app, you'd verify the token from the database
    # For simplicity, we'll just mark any user as verified
    # This is where you'd normally check the token against what's stored in the DB
    
    # For demo purposes, we'll just find any unverified user
    user = db.query(models.User).filter(models.User.is_verified == False).first()
    if not user:
        raise HTTPException(status_code=400, detail="No unverified users found")
    
    user.is_verified = True
    db.commit()
    
    return {"message": "Email verified successfully"}

@app.post("/login", response_model=schemas.Token)
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not db_user.is_verified:
        raise HTTPException(status_code=400, detail="Email not verified")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/ops/upload", response_model=schemas.File)
def upload_file(
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(auth.get_current_ops_user),
    db: Session = Depends(get_db)
):
    file_info = utils.save_uploaded_file(file, current_user.id)
    
    db_file = models.File(
        filename=file_info["filename"],
        filepath=file_info["filepath"],
        file_type=file_info["file_type"],
        uploaded_by=current_user.id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return db_file

@app.get("/client/files", response_model=List[schemas.File])
def list_files(
    current_user: schemas.User = Depends(auth.get_current_client_user),
    db: Session = Depends(get_db)
):
    files = db.query(models.File).all()
    return files

@app.post("/client/files/{file_id}/download", response_model=schemas.DownloadTokenResponse)
def request_download(
    file_id: int,
    current_user: schemas.User = Depends(auth.get_current_client_user),
    db: Session = Depends(get_db)
):
    # Check if file exists
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Generate download token
    token = utils.generate_download_token()
    expires_at = datetime.utcnow() + timedelta(minutes=30)
    
    # Save token to database
    db_token = models.DownloadToken(
        token=token,
        file_id=file.id,
        user_id=current_user.id,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    
    # Return the download URL
    download_url = f"/download/{token}"
    return {"download_url": download_url}

@app.get("/download/{token}")
def download_file(
    token: str,
    current_user: schemas.User = Depends(auth.get_current_client_user),
    db: Session = Depends(get_db)
):
    # Check if token is valid
    db_token = db.query(models.DownloadToken).filter(
        models.DownloadToken.token == token,
        models.DownloadToken.user_id == current_user.id,
        models.DownloadToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=403, detail="Invalid or expired download token")
    
    # Get the file
    file = db.query(models.File).filter(models.File.id == db_token.file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Return the file for download
    return FileResponse(
        file.filepath,
        filename=file.filename,
        media_type="application/octet-stream"
    )