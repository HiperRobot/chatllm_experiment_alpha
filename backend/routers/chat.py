from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.routers.auth import _get_token
from backend.models import Session as AuthSession, User
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.schemas.sessions import ChatSessionResponse as ChatSessionResp
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()


def _get_user(request: Request, db: Session) -> User | None:
    token = _get_token(request)
    if not token:
        return None
    auth_session = db.query(AuthSession).filter(AuthSession.session_token == token).first()
    if not auth_session:
        return None
    return db.query(User).filter(User.id == auth_session.user_id).first()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)) -> ChatResponse:
    user = _get_user(request, db)
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    # Resolve or create chat session
    session_id = payload.session_id
    title_generated = False
    chat_session = None

    if session_id:
        chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not chat_session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
        if chat_session.user_id is not None and (not user or user.id != chat_session.user_id):
            raise HTTPException(status_code=403, detail="Acesso negado.")
    else:
        chat_session = ChatSession(title="Nova conversa", user_id=user.id if user else None)
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        session_id = chat_session.id

    # Generate title from first user message if still default
    if chat_session.title == "Nova conversa":
        try:
            title_reply, _ = await generate_reply(
                user_message=f"Gere um titulo curto (max 6 palavras) para uma conversa que comeca com: {payload.message}",
                history=[],
                model=resolved_model,
            )
            chat_session.title = title_reply.strip().strip('"').strip("'")[:255]
            title_generated = True
        except Exception:
            chat_session.title = payload.message[:50]
            title_generated = True
        db.commit()

    try:
        reply, model_name = await generate_reply(
            user_message=payload.message,
            history=[item.model_dump() for item in payload.history],
            model=payload.model,
        )
    except OpenRouterConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    resolved_model = payload.model or model_name or OPENROUTER_MODEL_DEFAULT

    db.add(ChatMessage(chat_session_id=session_id, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(chat_session_id=session_id, role="assistant", content=reply, model=resolved_model))
    db.commit()

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request, db: Session = Depends(get_db)) -> StreamingResponse:
    user = _get_user(request, db)
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    # Resolve or create chat session
    session_id = payload.session_id
    title_generated = False
    chat_session = None

    if session_id:
        chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not chat_session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
        if chat_session.user_id is not None and (not user or user.id != chat_session.user_id):
            raise HTTPException(status_code=403, detail="Acesso negado.")
    else:
        chat_session = ChatSession(title="Nova conversa", user_id=user.id if user else None)
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        session_id = chat_session.id

    async def event_generator():
        nonlocal title_generated, chat_session
        full_reply = ""

        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=payload.model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=True)}\n\n"
        except OpenRouterConfigError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return

        # Generate title from first user message if still default
        if chat_session.title == "Nova conversa" and full_reply.strip():
            try:
                title_reply, _ = await generate_reply(
                    user_message=f"Gere um titulo curto (max 6 palavras) para uma conversa que comeca com: {payload.message}",
                    history=[],
                    model=resolved_model,
                )
                chat_session.title = title_reply.strip().strip('"').strip("'")[:255]
                title_generated = True
            except Exception:
                chat_session.title = payload.message[:50]
                title_generated = True

        if full_reply.strip():
            chat_session.updated_at = None  # will be auto-set by onupdate
            db.add(ChatMessage(chat_session_id=session_id, role="user", content=payload.message, model=resolved_model))
            db.add(ChatMessage(chat_session_id=session_id, role="assistant", content=full_reply, model=resolved_model))
            db.commit()

        yield f"data: {json.dumps({
            'done': True,
            'session_id': session_id,
            'title': chat_session.title,
            'title_generated': title_generated,
        }, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
