from __future__ import annotations

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Session as SessionModel
from backend.models import User
from backend.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/auth")

SESSION_COOKIE = "session_token"


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _get_token(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


def _set_session_cookie(response: Response, session_token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
        path="/",
    )


def _delete_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


@router.post("/register", response_model=AuthResponse)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    if payload.password != payload.password_confirm:
        raise HTTPException(status_code=400, detail="As senhas nao conferem.")

    existing = db.query(User).filter(User.username == payload.username.strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Usuario ja cadastrado.")

    user = User(
        username=payload.username.strip(),
        password_hash=_hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    session = SessionModel(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    _set_session_cookie(response, session.session_token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        session_token=session.session_token,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Usuario nao cadastrado. Cadastre-se primeiro.",
        )

    if not _check_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Senha incorreta.")

    session = SessionModel(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    _set_session_cookie(response, session.session_token)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        session_token=session.session_token,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> MessageResponse:
    token = _get_token(request)
    if token:
        session = db.query(SessionModel).filter(SessionModel.session_token == token).first()
        if session:
            db.delete(session)
            db.commit()

    _delete_session_cookie(response)
    return MessageResponse(message="Logout realizado com sucesso.")


@router.get("/me", response_model=MeResponse)
def me(request: Request, db: Session = Depends(get_db)) -> MeResponse:
    token = _get_token(request)
    if not token:
        return MeResponse(user=None)

    session = db.query(SessionModel).filter(SessionModel.session_token == token).first()
    if not session:
        return MeResponse(user=None)

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        return MeResponse(user=None)

    return MeResponse(user=UserResponse.model_validate(user))