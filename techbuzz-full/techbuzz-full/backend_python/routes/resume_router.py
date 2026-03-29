"""
Resume Builder Router
=====================
Provides user-owned resume CRUD, listing, deletion, and AI-powered
improvement endpoints. Each resume is tied to an authenticated member
user; access is always filtered by user_id.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional


router = APIRouter(prefix="/api/resume", tags=["resume"])

# Maximum characters of resume content sent to the AI provider.
MAX_RESUME_CONTENT_FOR_AI = 6000


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class ResumeCreateRequest(BaseModel):
    title: str
    content: str
    target_role: str = ""


class ResumeUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    target_role: Optional[str] = None


class ResumeImproveRequest(BaseModel):
    instruction: str = ""


# ---------------------------------------------------------------------------
# Internal helpers (populated by install_resume_router)
# ---------------------------------------------------------------------------

_ctx: dict = {}


def _db_exec(query: str, params: tuple = ()) -> None:
    _ctx["db_exec"](query, params)


def _db_one(query: str, params: tuple = ()) -> Optional[dict]:
    return _ctx["db_one"](query, params)


def _db_all(query: str, params: tuple = ()) -> list:
    return _ctx["db_all"](query, params)


def _session_user(request: Request) -> Optional[dict]:
    return _ctx["session_user"](request)


def _new_id(prefix: str) -> str:
    return _ctx["new_id"](prefix)


def _now_iso() -> str:
    return _ctx["now_iso"]()


def _get_resume_for_user(user_id: str, resume_id: str) -> dict:
    """Fetch a resume by id, ensuring it belongs to user_id."""
    row = _db_one(
        "SELECT * FROM resumes WHERE id=? AND user_id=?",
        (resume_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return row


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/create")
async def resume_create(req: ResumeCreateRequest, request: Request):
    viewer = _session_user(request)
    if not viewer:
        raise HTTPException(status_code=401, detail="Login required to create a resume.")
    title = (req.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="A title is required.")
    content = (req.content or "").strip()
    resume_id = _new_id("rsm")
    now = _now_iso()
    _db_exec(
        "INSERT INTO resumes(id,user_id,title,content,target_role,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        (resume_id, viewer["id"], title, content, (req.target_role or "").strip(), now, now),
    )
    return {"resume": _db_one("SELECT * FROM resumes WHERE id=?", (resume_id,)), "message": "Resume created."}


@router.get("/list")
async def resume_list(request: Request):
    viewer = _session_user(request)
    if not viewer:
        raise HTTPException(status_code=401, detail="Login required to list resumes.")
    rows = _db_all(
        "SELECT id,user_id,title,target_role,created_at,updated_at FROM resumes WHERE user_id=? ORDER BY updated_at DESC",
        (viewer["id"],),
    )
    return {"resumes": rows}


@router.get("/{resume_id}")
async def resume_get(resume_id: str, request: Request):
    viewer = _session_user(request)
    if not viewer:
        raise HTTPException(status_code=401, detail="Login required to view a resume.")
    return {"resume": _get_resume_for_user(viewer["id"], resume_id)}


@router.put("/{resume_id}")
async def resume_update(resume_id: str, req: ResumeUpdateRequest, request: Request):
    viewer = _session_user(request)
    if not viewer:
        raise HTTPException(status_code=401, detail="Login required to update a resume.")
    existing = _get_resume_for_user(viewer["id"], resume_id)
    new_title = (req.title or "").strip() if req.title is not None else existing["title"]
    new_content = req.content if req.content is not None else existing["content"]
    new_role = (req.target_role or "").strip() if req.target_role is not None else existing["target_role"]
    if not new_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    _db_exec(
        "UPDATE resumes SET title=?,content=?,target_role=?,updated_at=? WHERE id=? AND user_id=?",
        (new_title, new_content, new_role, _now_iso(), resume_id, viewer["id"]),
    )
    return {"resume": _db_one("SELECT * FROM resumes WHERE id=?", (resume_id,)), "message": "Resume updated."}


@router.delete("/{resume_id}")
async def resume_delete(resume_id: str, request: Request):
    viewer = _session_user(request)
    if not viewer:
        raise HTTPException(status_code=401, detail="Login required to delete a resume.")
    _get_resume_for_user(viewer["id"], resume_id)  # ownership check
    _db_exec(
        "DELETE FROM resumes WHERE id=? AND user_id=?",
        (resume_id, viewer["id"]),
    )
    return {"message": "Resume deleted."}


@router.post("/{resume_id}/improve")
async def resume_improve(resume_id: str, req: ResumeImproveRequest, request: Request):
    viewer = _session_user(request)
    if not viewer:
        raise HTTPException(status_code=401, detail="Login required to improve a resume.")
    resume = _get_resume_for_user(viewer["id"], resume_id)
    generate_text = _ctx.get("generate_text")
    if not generate_text:
        raise HTTPException(status_code=503, detail="AI text generation is not available.")
    content = (resume.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Resume has no content to improve.")
    instruction = (req.instruction or "").strip() or "Improve clarity, impact, and ATS compatibility."
    target_role = (resume.get("target_role") or "").strip()
    role_hint = f" The target role is: {target_role}." if target_role else ""
    system = (
        "You are a professional resume writer. "
        "Rewrite or improve the provided resume text to be clear, impactful, and ATS-friendly."
        + role_hint
        + " Return only the improved resume text, preserving all key facts."
    )
    prompt = f"Instruction: {instruction}\n\nResume:\n{content[:MAX_RESUME_CONTENT_FOR_AI]}"
    result = await generate_text(prompt, system=system, max_tokens=2048, source="manual")
    improved = (result.get("text") or "").strip()
    if not improved:
        raise HTTPException(status_code=503, detail="AI did not return an improvement. Please try again.")
    _db_exec(
        "UPDATE resumes SET content=?,updated_at=? WHERE id=? AND user_id=?",
        (improved, _now_iso(), resume_id, viewer["id"]),
    )
    return {
        "resume": _db_one("SELECT * FROM resumes WHERE id=?", (resume_id,)),
        "improved_text": improved,
        "provider": result.get("provider", "unknown"),
        "message": "Resume improved by AI.",
    }


# ---------------------------------------------------------------------------
# Installer (called from app.py)
# ---------------------------------------------------------------------------

def install_resume_router(app, ctx: dict) -> None:
    """Register the resume router and inject context helpers."""
    _ctx.update(ctx)
    app.include_router(router)
