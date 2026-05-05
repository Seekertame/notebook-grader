from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from pydantic import BaseModel, EmailStr, Field

from app.models.domain import Teacher

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=100)
    password: str = Field(min_length=8, max_length=64)
    display_name: str | None = None


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Teacher).filter(Teacher.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    teacher = Teacher(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        display_name=data.display_name,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    token = create_access_token(data={"sub": teacher.email})
    return {
        "id": teacher.id,
        "email": teacher.email,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    teacher = db.query(Teacher).filter(Teacher.email == form_data.username).first()
    if teacher is None or not verify_password(form_data.password, teacher.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": teacher.email})
    return {"access_token": token, "token_type": "bearer"}
