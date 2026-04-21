"""Auth routes – register / login for HIS A doctors."""

import asyncpg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.database import get_pool

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=status.HTTP_201_CREATED,
    summary="Register a new doctor account",
    description="สร้าง user ใหม่สำหรับหมอ\n\n**ตัวอย่าง body:**\n```json\n{\n  \"username\": \"doctor01\",\n  \"password\": \"password123\",\n  \"full_name\": \"นพ.สมชาย ใจดี\"\n}\n```")
async def register(body: RegisterRequest) -> dict:
    pool = get_pool()
    hashed = get_password_hash(body.password)
    try:
        await pool.execute(
            "INSERT INTO users (username, full_name, hashed_password) VALUES ($1, $2, $3)",
            body.username,
            body.full_name,
            hashed,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        )
    return {"detail": "User created successfully."}


@router.post("/login", response_model=TokenResponse,
    summary="Login and get JWT token",
    description="Login แล้วได้ JWT token สำหรับเรียก FHIR endpoints\n\n**Seed account (พร้อมใช้ได้เลย):**\n```json\n{\n  \"username\": \"admin\",\n  \"password\": \"admin1234\"\n}\n```\n\nนำ `access_token` ที่ได้ไปกด **Authorize** แล้วใส่เป็น `Bearer <token>`")
async def login(body: LoginRequest) -> TokenResponse:
    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT hashed_password FROM users WHERE username = $1", body.username
    )
    if not row or not verify_password(body.password, row["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )
    token = create_access_token(subject=body.username)
    return TokenResponse(access_token=token)
