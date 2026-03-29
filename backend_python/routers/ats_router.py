"""
ATS (Applicant Tracking System) router.

Handles /api/ats/* endpoints (master-only):
  - Job management: create, list
  - Candidate management: create, move stage, delete, import from Praapti
  - AI scoring: batch score all candidates
"""
import json
import re
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ATSJobReq(BaseModel):
    title: str
    department: str = ""
    location: str = "India"
    description: str = ""
    urgency: str = "normal"


class ATSCandidateReq(BaseModel):
    name: str
    email: str = ""
    role: str = ""
    experience: int = 0
    status: str = "applied"
    job_id: str = ""
    resume_text: str = ""
    source: str = "manual"


class ATSMoveReq(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_ats_router(ctx: Dict[str, Any]) -> APIRouter:
    """Return an APIRouter with all /api/ats/* routes registered."""

    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    generate_text = ctx["generate_text"]
    get_state = ctx["get_state"]
    ai_name = ctx["AI_NAME"]
    company_name = ctx["COMPANY_NAME"]
    core_identity = ctx["CORE_IDENTITY"]
    emit_carbon = ctx["emit_carbon"]

    router = APIRouter()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def require_master(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user or user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Imperial access required")
        return user

    async def ai_text(prompt: str, *, workspace: str, source: str, max_tokens: int = 500) -> Dict[str, Any]:
        return await generate_text(
            prompt,
            system=(
                f"You are {ai_name}, the {core_identity} mother-brain of {company_name}. "
                "Be specific, practical, and structured. Prefer actionable outputs over vague metaphors."
            ),
            max_tokens=max_tokens,
            use_web_search=False,
            workspace=workspace,
            source=source,
        )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @router.get("/api/ats/state")
    async def ats_get_state(request: Request):
        user = require_master(request)
        jobs = db_all("SELECT * FROM ats_jobs WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        cands = db_all("SELECT * FROM ats_candidates WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        stages = ["applied", "screening", "interview", "offer", "hired", "rejected"]
        return {
            "jobs": jobs,
            "candidates": cands,
            "pipeline_counts": {stage: len([c for c in cands if c.get("status") == stage]) for stage in stages},
            "total_candidates": len(cands),
            "open_jobs": len([job for job in jobs if job.get("status") == "open"]),
        }

    @router.post("/api/ats/jobs")
    async def ats_add_job(req: ATSJobReq, request: Request):
        user = require_master(request)
        result = await ai_text(
            (
                f"Write a compelling, specific job description for {req.title} at {company_name}.\n"
                f"Department: {req.department}\nLocation: {req.location}\nUrgency: {req.urgency}\n"
                f"Additional context: {req.description}\n"
                "Keep it useful for a real ATS posting."
            ),
            workspace="ats",
            source="ats_job",
            max_tokens=520,
        )
        job_id = new_id("job")
        description = result["text"] or req.description
        db_exec(
            """
            INSERT INTO ats_jobs(id,user_id,title,department,location,description,urgency,status,ai_profile,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (job_id, user["id"], req.title, req.department, req.location, description, req.urgency, "open", description[:320], now_iso(), now_iso()),
        )
        emit_carbon("ats_job_posted", {"title": req.title}, "nanotube")
        return {"ok": True, "id": job_id, "description": description, "provider": result["provider"]}

    @router.post("/api/ats/candidates")
    async def ats_add_candidate(req: ATSCandidateReq, request: Request):
        user = require_master(request)
        result = await ai_text(
            (
                f"Evaluate this candidate for the role {req.role} at {company_name}.\n"
                f"Name: {req.name}\nExperience: {req.experience} years\nResume: {req.resume_text[:900] or 'Not provided'}\n"
                'Return strict JSON: {"fit": 82, "strength": "...", "concern": "..."}'
            ),
            workspace="ats",
            source="ats_candidate",
            max_tokens=180,
        )
        parsed: Dict[str, Any] = {}
        try:
            match = re.search(r"\{[\s\S]+\}", result["text"] or "")
            parsed = json.loads(match.group(0)) if match else {}
        except Exception:
            parsed = {}
        fit = max(40, min(99, int(parsed.get("fit", 70))))
        strength = str(parsed.get("strength", ""))[:200]
        concern = str(parsed.get("concern", ""))[:200]
        candidate_id = new_id("cand")
        db_exec(
            """
            INSERT INTO ats_candidates(id,user_id,job_id,name,email,role,experience,fit_score,status,ai_strength,ai_concern,source,resume_text,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                candidate_id,
                user["id"],
                req.job_id,
                req.name,
                req.email,
                req.role,
                req.experience,
                fit,
                req.status,
                strength,
                concern,
                req.source,
                req.resume_text[:4000],
                now_iso(),
                now_iso(),
            ),
        )
        emit_carbon("candidate_added", {"name": req.name, "fit": fit}, "nanotube")
        return {"ok": True, "id": candidate_id, "fit_score": fit, "strength": strength, "concern": concern, "provider": result["provider"]}

    @router.put("/api/ats/candidates/{candidate_id}/move")
    async def ats_move_candidate(candidate_id: str, req: ATSMoveReq, request: Request):
        user = require_master(request)
        db_exec("UPDATE ats_candidates SET status=?, updated_at=? WHERE id=? AND user_id=?", (req.status, now_iso(), candidate_id, user["id"]))
        emit_carbon("candidate_moved", {"id": candidate_id, "status": req.status}, "nanotube")
        return {"ok": True, "id": candidate_id, "status": req.status}

    @router.delete("/api/ats/candidates/{candidate_id}")
    async def ats_delete_candidate(candidate_id: str, request: Request):
        user = require_master(request)
        db_exec("DELETE FROM ats_candidates WHERE id=? AND user_id=?", (candidate_id, user["id"]))
        return {"ok": True}

    @router.post("/api/ats/import-praapti")
    async def ats_import_praapti(request: Request):
        user = require_master(request)
        state = get_state()
        hunts = state.get("praapti_hunts", [])
        if not hunts:
            raise HTTPException(status_code=404, detail="No Praapti hunts found")
        hunt = hunts[-1]
        imported: List[Dict[str, Any]] = []
        existing = {
            (row.get("name", "").strip().lower(), row.get("role", "").strip().lower())
            for row in (db_all("SELECT name,role FROM ats_candidates WHERE user_id=?", (user["id"],)) or [])
        }
        for cand in hunt.get("candidates", []):
            key = (cand.get("name", "").strip().lower(), cand.get("title", "").strip().lower())
            if key in existing:
                continue
            cid = new_id("cand")
            db_exec(
                """
                INSERT INTO ats_candidates(id,user_id,job_id,name,email,role,experience,fit_score,status,ai_strength,ai_concern,source,resume_text,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    cid,
                    user["id"],
                    "",
                    cand.get("name", "Unknown"),
                    "",
                    cand.get("title", ""),
                    int(cand.get("experience", 0) or 0),
                    int(cand.get("fit_score", 70) or 70),
                    "applied",
                    str(cand.get("genesis_profile", ""))[:220],
                    "",
                    "praapti",
                    "",
                    now_iso(),
                    now_iso(),
                ),
            )
            imported.append({"id": cid, "name": cand.get("name"), "fit_score": cand.get("fit_score", 70)})
        emit_carbon("praapti_imported", {"count": len(imported)}, "nanotube")
        return {"ok": True, "imported": len(imported), "candidates": imported}

    @router.post("/api/ats/ai-score-all")
    async def ats_ai_score_all(request: Request):
        user = require_master(request)
        candidates = db_all("SELECT * FROM ats_candidates WHERE user_id=? ORDER BY updated_at DESC LIMIT 25", (user["id"],)) or []
        updated = 0
        for cand in candidates:
            result = await ai_text(
                (
                    f"Quick fit score for candidate {cand['name']}.\n"
                    f"Role: {cand.get('role', '')}\nExperience: {cand.get('experience', 0)} years\n"
                    'Return strict JSON: {"fit": 78}'
                ),
                workspace="ats",
                source="ats_score",
                max_tokens=80,
            )
            match = re.search(r"\d+", result["text"] or "")
            if not match:
                continue
            score = max(40, min(99, int(match.group(0))))
            db_exec("UPDATE ats_candidates SET fit_score=?, updated_at=? WHERE id=? AND user_id=?", (score, now_iso(), cand["id"], user["id"]))
            updated += 1
        return {"ok": True, "updated": updated, "mode": "diamond"}

    return router
