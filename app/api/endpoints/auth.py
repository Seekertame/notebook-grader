import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import create_access_token, get_password_hash, verify_password
from pydantic import BaseModel, EmailStr, Field

from app.models.domain import Teacher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "<invalid>"
    local, _, domain = email.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


class RegisterRequest(BaseModel):
    email: EmailStr = Field(max_length=100)
    password: str = Field(min_length=8, max_length=64)
    display_name: str | None = None


@router.post("/register")
@limiter.limit("5/hour")
def register(
    request: Request,
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(Teacher).filter(Teacher.email == data.email).first()
    if existing:
        logger.warning("register conflict: email=%s", _mask_email(data.email))
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

    logger.info("user registered: teacher_id=%d", teacher.id)

    token = create_access_token(data={"sub": teacher.email})
    return {
        "id": teacher.id,
        "email": teacher.email,
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/login")
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    teacher = db.query(Teacher).filter(Teacher.email == form_data.username).first()
    if teacher is None or not verify_password(form_data.password, teacher.hashed_password):
        logger.warning("login failed: email=%s", _mask_email(form_data.username))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("login success: teacher_id=%d", teacher.id)
    token = create_access_token(data={"sub": teacher.email})
    return {"access_token": token, "token_type": "bearer"}
