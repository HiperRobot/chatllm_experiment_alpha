from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.config import SQLITE_PATH
from backend.database import Base, engine
from backend.routers.auth import router as auth_router
from backend.routers.chat import router as chat_router
from backend.routers.sessions import router as sessions_router


Base.metadata.create_all(bind=engine)


def _migrate_chat_message_sessions() -> None:
    db_path = Path(SQLITE_PATH)
    if not db_path.exists():
        return

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(chat_messages)")}
        if "chat_session_id" in columns or "session_key" not in columns:
            return

        try:
            connection.execute("ALTER TABLE chat_messages ADD COLUMN chat_session_id INTEGER")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
            return
        legacy_keys = [
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT session_key FROM chat_messages ORDER BY session_key"
            )
        ]
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")

        for legacy_key in legacy_keys:
            title = "Nova conversa" if legacy_key == "default" else f"Conversa {legacy_key}"
            cursor = connection.execute(
                "INSERT INTO chat_sessions (title, user_id, created_at, updated_at) VALUES (?, NULL, ?, ?)",
                (title, now, now),
            )
            connection.execute(
                "UPDATE chat_messages SET chat_session_id = ? WHERE session_key = ?",
                (cursor.lastrowid, legacy_key),
            )

        connection.commit()


_migrate_chat_message_sessions()

app = FastAPI(title="ChatLLM Experiment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheMiddleware)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(sessions_router)

NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/")
def root() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html nao encontrado")
    return FileResponse(index_path, headers=NO_CACHE_HEADERS)
