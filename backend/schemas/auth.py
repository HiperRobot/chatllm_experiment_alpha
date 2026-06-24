from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255, pattern=r"^\S+$")
    password: str = Field(min_length=1, max_length=255)
    password_confirm: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse
    session_token: str


class MeResponse(BaseModel):
    user: UserResponse | None = None


class MessageResponse(BaseModel):
    message: str