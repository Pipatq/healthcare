from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

import asyncpg

from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.database import get_pool

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest) -> dict:
    pool = get_pool()
    hashed = get_password_hash(body.password)
    try:
        await pool.execute(
            "INSERT INTO users (username, hashed_password) VALUES ($1, $2)",
            body.username,
            hashed,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        )
    return {"detail": "User created successfully."}


@router.post("/login", response_model=TokenResponse)
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
