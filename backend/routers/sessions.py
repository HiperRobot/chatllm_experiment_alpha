from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatSession as ChatSessionModel
from backend.models import User
from backend.schemas.sessions import (
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from backend.routers.auth import _get_token, SESSION_COOKIE

router = APIRouter(prefix="/api/sessions")


def _next_default_title(db: Session, user_id: int | None) -> str:
    base_title = "Nova conversa"
    query = db.query(ChatSessionModel.title)
    if user_id is None:
        query = query.filter(ChatSessionModel.user_id.is_(None))
    else:
        query = query.filter(ChatSessionModel.user_id == user_id)

    titles = [row[0] for row in query.filter(ChatSessionModel.title.like("Nova conversa%")).all()]
    taken_indexes = set()
    pattern = re.compile(r"^Nova conversa \((\d+)\)$")

    for title in titles:
        if title == base_title:
            taken_indexes.add(0)
            continue
        match = pattern.match(title)
        if match:
            taken_indexes.add(int(match.group(1)))

    if 0 not in taken_indexes:
        return base_title

    index = 1
    while index in taken_indexes:
        index += 1
    return f"Nova conversa ({index})"


def _get_user(request: Request, db: Session) -> User | None:
    """Get the authenticated user from the session cookie, if any."""
    token = _get_token(request)
    if not token:
        return None
    from backend.models import Session as AuthSession
    auth_session = db.query(AuthSession).filter(AuthSession.session_token == token).first()
    if not auth_session:
        return None
    return db.query(User).filter(User.id == auth_session.user_id).first()


@router.get("", response_model=ChatSessionListResponse)
def list_sessions(request: Request, db: Session = Depends(get_db)) -> ChatSessionListResponse:
    user = _get_user(request, db)
    if user:
        sessions = (
            db.query(ChatSessionModel)
            .filter(ChatSessionModel.user_id == user.id)
            .order_by(ChatSessionModel.updated_at.desc())
            .all()
        )
    else:
        sessions = []

    return ChatSessionListResponse(
        sessions=[ChatSessionResponse.model_validate(s) for s in sessions]
    )


@router.post("", response_model=ChatSessionResponse, status_code=201)
def create_session(
    payload: ChatSessionCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ChatSessionResponse:
    user = _get_user(request, db)
    title = payload.title or _next_default_title(db, user.id if user else None)
    chat_session = ChatSessionModel(
        title=title,
        user_id=user.id if user else None,
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return ChatSessionResponse.model_validate(chat_session)


@router.get("/{session_id}")
def get_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    user = _get_user(request, db)
    chat_session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")

    if chat_session.user_id is not None:
        if not user or user.id != chat_session.user_id:
            raise HTTPException(status_code=403, detail="Acesso negado a esta sessao.")

    from backend.schemas.sessions import ChatSessionDetailResponse, ChatSessionMessageResponse

    # Force load messages
    msgs = sorted(chat_session.messages, key=lambda x: x.created_at or x.id)

    return ChatSessionDetailResponse(
        session=ChatSessionResponse.model_validate(chat_session),
        messages=[ChatSessionMessageResponse.model_validate(m) for m in msgs],
    ).model_dump(mode="json")


@router.patch("/{session_id}", response_model=ChatSessionResponse)
def update_session(
    session_id: int,
    payload: ChatSessionUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> ChatSessionResponse:
    user = _get_user(request, db)
    chat_session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")

    if chat_session.user_id is not None:
        if not user or user.id != chat_session.user_id:
            raise HTTPException(status_code=403, detail="Acesso negado.")

    if payload.title is not None:
        chat_session.title = payload.title
    db.commit()
    db.refresh(chat_session)
    return ChatSessionResponse.model_validate(chat_session)


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    user = _get_user(request, db)
    chat_session = db.query(ChatSessionModel).filter(ChatSessionModel.id == session_id).first()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")

    if chat_session.user_id is not None:
        if not user or user.id != chat_session.user_id:
            raise HTTPException(status_code=403, detail="Acesso negado.")

    db.delete(chat_session)
    db.commit()
    return {"message": "Sessao deletada com sucesso."}