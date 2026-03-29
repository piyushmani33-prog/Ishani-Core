"""
Resume Builder Layer
====================
Provides minimal resume creation, retrieval, update, and optional AI improvement.
Stores resume data in the shared SQLite database.
"""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


class ResumeCreateRequest(BaseModel):
    name: str
    title: str = ""
    summary: str = ""
    skills: str = ""
    experience: str = ""


class ResumeUpdateRequest(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[str] = None
    experience: Optional[str] = None


class ResumeImproveRequest(BaseModel):
    resume_id: str
    fields: List[str] = ["summary", "experience"]


def install_resume_layer(app, ctx: Dict[str, Any]) -> None:
    db_exec = ctx["db_exec"]
    db_one = ctx["db_one"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    generate_text = ctx["generate_text"]
    log = ctx["log"]

    db_exec(
        """
        CREATE TABLE IF NOT EXISTS resumes (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL DEFAULT '',
            title       TEXT NOT NULL DEFAULT '',
            summary     TEXT NOT NULL DEFAULT '',
            skills      TEXT NOT NULL DEFAULT '',
            experience  TEXT NOT NULL DEFAULT '',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )

    @app.post("/api/resume/create")
    async def resume_create(req: ResumeCreateRequest, request: Request):
        resume_id = new_id("rsm")
        ts = now_iso()
        db_exec(
            """
            INSERT INTO resumes (id, name, title, summary, skills, experience, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resume_id,
                req.name.strip(),
                req.title.strip(),
                req.summary.strip(),
                req.skills.strip(),
                req.experience.strip(),
                ts,
                ts,
            ),
        )
        log.info("Resume created: %s", resume_id)
        row = db_one("SELECT * FROM resumes WHERE id=?", (resume_id,))
        return {"ok": True, "resume": row}

    @app.get("/api/resume/{resume_id}")
    async def resume_get(resume_id: str, request: Request):
        row = db_one("SELECT * FROM resumes WHERE id=?", (resume_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Resume not found.")
        return {"ok": True, "resume": row}

    @app.put("/api/resume/{resume_id}")
    async def resume_update(resume_id: str, req: ResumeUpdateRequest, request: Request):
        row = db_one("SELECT * FROM resumes WHERE id=?", (resume_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Resume not found.")
        ts = now_iso()
        db_exec(
            """
            UPDATE resumes
            SET name       = COALESCE(?, name),
                title      = COALESCE(?, title),
                summary    = COALESCE(?, summary),
                skills     = COALESCE(?, skills),
                experience = COALESCE(?, experience),
                updated_at = ?
            WHERE id = ?
            """,
            (
                req.name.strip() or None if req.name is not None else None,
                req.title.strip() or None if req.title is not None else None,
                req.summary.strip() or None if req.summary is not None else None,
                req.skills.strip() or None if req.skills is not None else None,
                req.experience.strip() or None if req.experience is not None else None,
                ts,
                resume_id,
            ),
        )
        updated = db_one("SELECT * FROM resumes WHERE id=?", (resume_id,))
        return {"ok": True, "resume": updated}

    @app.post("/api/resume/improve")
    async def resume_improve(req: ResumeImproveRequest, request: Request):
        row = db_one("SELECT * FROM resumes WHERE id=?", (req.resume_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Resume not found.")

        allowed_fields = {"summary", "experience"}
        fields_to_improve = [f for f in req.fields if f in allowed_fields]
        if not fields_to_improve:
            raise HTTPException(status_code=400, detail="Specify at least one of: summary, experience.")

        improvements: Dict[str, str] = {}
        for field in fields_to_improve:
            original = row.get(field, "").strip()
            if not original:
                improvements[field] = original
                continue
            system_prompt = (
                "You are a professional resume writer. "
                "Rewrite the provided resume section to be concise, impactful, and ATS-friendly. "
                "Return only the improved text — no extra commentary."
            )
            prompt = (
                f"Name: {row.get('name', '')}\n"
                f"Title: {row.get('title', '')}\n\n"
                f"Improve this resume {field} section:\n{original}"
            )
            result = await generate_text(prompt, system=system_prompt, max_tokens=512, source="system")
            improvements[field] = result.get("text", original).strip() or original

        ts = now_iso()
        if improvements:
            set_clauses = ", ".join(f"{field} = ?" for field in improvements)
            params = list(improvements.values()) + [ts, req.resume_id]
            db_exec(
                f"UPDATE resumes SET {set_clauses}, updated_at = ? WHERE id = ?",
                tuple(params),
            )

        updated = db_one("SELECT * FROM resumes WHERE id=?", (req.resume_id,))
        return {"ok": True, "resume": updated, "improved_fields": list(improvements.keys())}
