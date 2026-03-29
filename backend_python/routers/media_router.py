"""
Media router – media library management + media page.

Handles:
  GET  /media                — Serve the media HTML page (member-only)
  POST /api/media/save       — Save a media item to the library
  GET  /api/media/library    — List the user's saved media items
  PUT  /api/media/play/{id}  — Increment play count for a media item
"""
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class MediaSaveReq(BaseModel):
    title: str = ""
    media_type: str = "video"
    url: str = ""
    thumbnail: str = ""
    duration: str = ""
    source: str = ""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_media_router(ctx: Dict[str, Any]) -> APIRouter:
    """Return an APIRouter with /media page and /api/media/* routes."""

    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    frontend_dir = Path(ctx["FRONTEND_DIR"])

    router = APIRouter()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def require_member(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        return user

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @router.get("/media")
    async def media_page(request: Request):
        require_member(request)
        path = frontend_dir / "media.html"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Media page not found")
        return FileResponse(path)

    @router.post("/api/media/save")
    async def media_save(req: MediaSaveReq, request: Request):
        user = require_member(request)
        media_id = new_id("med")
        db_exec(
            """
            INSERT INTO media_library(id,user_id,title,media_type,url,thumbnail,duration,source,added_at,play_count,last_played)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (media_id, user["id"], req.title[:220], req.media_type, req.url[:800], req.thumbnail[:500], req.duration[:100], req.source[:120], now_iso(), 1, now_iso()),
        )
        return {"ok": True, "id": media_id}

    @router.get("/api/media/library")
    async def media_library(request: Request):
        user = require_member(request)
        items = db_all("SELECT * FROM media_library WHERE user_id=? ORDER BY added_at DESC LIMIT 40", (user["id"],)) or []
        return {"items": items, "total": len(items)}

    @router.put("/api/media/play/{media_id}")
    async def media_play_count(media_id: str, request: Request):
        user = require_member(request)
        db_exec("UPDATE media_library SET play_count=play_count+1,last_played=? WHERE id=? AND user_id=?", (now_iso(), media_id, user["id"]))
        return {"ok": True}

    return router
