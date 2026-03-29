import asyncio
import json
import re
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote_plus

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel


CARBON_MODES = {
    "graphene": {
        "name": "Graphene-Mind",
        "desc": "Mass parallel signal mesh across the empire.",
        "use": "Network signals, broad intelligence, multi-lane scanning.",
        "color": "#90f2d2",
    },
    "diamond": {
        "name": "Diamond-Mind",
        "desc": "Deep single-focus analysis with hard precision.",
        "use": "Scoring, strategy, difficult planning, critical review.",
        "color": "#87dfff",
    },
    "nanotube": {
        "name": "Nanotube-Mind",
        "desc": "Zero-loss relay between connected systems and stages.",
        "use": "Pipelines, imports, logistics, controlled flow.",
        "color": "#c1a1ff",
    },
}

NEWS_FEEDS = {
    "tech": [
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
    "india_business": [
        "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "https://www.thehindubusinessline.com/feeder/default.rss",
    ],
    "hiring": [
        "https://www.linkedin.com/news/rss/",
        "https://blog.indeed.com/feed/",
    ],
    "ai": [
        "https://www.marktechpost.com/feed/",
        "https://openai.com/news/rss.xml",
    ],
}


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


class NetworkPostReq(BaseModel):
    content: str
    kind: str = "post"


class NetworkConnReq(BaseModel):
    name: str
    title: str = ""
    company: str = ""
    linkedin: str = ""
    notes: str = ""


class NetworkSignalReq(BaseModel):
    query: str
    mode: str = "graphene"


class HQClientReq(BaseModel):
    name: str
    industry: str = ""
    value: float = 0
    stage: str = "prospect"
    contact: str = ""
    notes: str = ""


class HQClientMoveReq(BaseModel):
    stage: str


class HQRevenueReq(BaseModel):
    type: str = "revenue"
    amount: float
    source: str = ""
    category: str = ""


class HQTeamReq(BaseModel):
    name: str
    role: str = ""
    email: str = ""
    department: str = ""


class CarbonBondReq(BaseModel):
    bond_type: str = "data"
    source_system: str
    target_system: str
    protocol_mode: str = "graphene"
    signal: str = ""


class CarbonThinkReq(BaseModel):
    mode: str = "graphene"
    problem: str = ""


class IntelSearchReq(BaseModel):
    query: str
    brain_id: str = "sec_signals"
    engine: str = "web"


class IntelNewsReq(BaseModel):
    category: str = "tech"
    brain_id: str = "sec_anveshan"


class IntelFetchReq(BaseModel):
    url: str
    brain_id: str = "tool_researcher"


class MediaSaveReq(BaseModel):
    title: str
    media_type: str = "youtube"
    url: str
    thumbnail: str = ""
    duration: str = ""
    source: str = ""


def install_empire_merge_layer(app, ctx: Dict[str, Any]) -> None:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    generate_text = ctx["generate_text"]
    get_state = ctx["get_state"]
    frontend_dir = Path(ctx["FRONTEND_DIR"])
    ai_name = ctx["AI_NAME"]
    company_name = ctx["COMPANY_NAME"]
    core_identity = ctx["CORE_IDENTITY"]
    log = ctx["log"]

    carbon_events: List[Dict[str, Any]] = []

    def require_master(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user or user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Imperial access required")
        return user

    def require_member(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        return user

    async def ai_text(
        prompt: str,
        *,
        workspace: str,
        source: str,
        max_tokens: int = 500,
        use_web_search: bool = False,
    ) -> Dict[str, Any]:
        return await generate_text(
            prompt,
            system=(
                f"You are {ai_name}, the {core_identity} mother-brain of {company_name}. "
                "Be specific, practical, and structured. Prefer actionable outputs over vague metaphors."
            ),
            max_tokens=max_tokens,
            use_web_search=use_web_search,
            workspace=workspace,
            source=source,
        )

    def emit_carbon(kind: str, payload: Dict[str, Any], mode: str = "graphene") -> None:
        event = {
            "id": new_id("carbon"),
            "kind": kind,
            "payload": payload,
            "mode": mode,
            "at": now_iso(),
        }
        carbon_events.append(event)
        if len(carbon_events) > 120:
            del carbon_events[:-120]
        try:
            db_exec(
                """
                INSERT INTO carbon_events(id,event_type,payload,carbon_mode,created_at)
                VALUES(?,?,?,?,?)
                """,
                (
                    event["id"],
                    kind,
                    json.dumps(payload, ensure_ascii=False)[:4000],
                    mode,
                    event["at"],
                ),
            )
        except Exception:
            pass

    def cleanup_text(value: str) -> str:
        text = unescape(re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", value, flags=re.I))
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    async def ddg_search(query: str) -> List[Dict[str, str]]:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TechBuzz-Ishani/1.0"})
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Web search unavailable")
        html = response.text
        blocks = re.findall(
            r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>[\s\S]{0,800}?<a[^>]*class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
            html,
            flags=re.I,
        )
        results: List[Dict[str, str]] = []
        for href, title, snippet in blocks[:6]:
            results.append(
                {
                    "title": cleanup_text(title),
                    "url": href,
                    "snippet": cleanup_text(snippet),
                }
            )
        return results

    async def fetch_rss_items(feed_url: str, limit: int = 5) -> List[Dict[str, str]]:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(feed_url, headers={"User-Agent": "TechBuzz-Ishani/1.0"})
        if response.status_code >= 400:
            return []
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            return []
        items: List[Dict[str, str]] = []
        for item in root.findall(".//item")[:limit]:
            items.append(
                {
                    "title": cleanup_text(item.findtext("title", "") or ""),
                    "url": item.findtext("link", "") or "",
                    "snippet": cleanup_text(item.findtext("description", "") or "")[:400],
                    "published_at": item.findtext("pubDate", "") or "",
                }
            )
        return items

    async def fetch_url_text(url: str) -> str:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "TechBuzz-Ishani/1.0"})
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail="Could not fetch URL content")
        return cleanup_text(response.text)[:8000]

    def store_brain_knowledge(
        brain_id: str,
        source_type: str,
        title: str,
        source_url: str,
        content: str,
        summary: str,
        keywords: str = "",
        relevance_score: float = 0.7,
    ) -> str:
        kid = new_id("bk")
        db_exec(
            """
            INSERT INTO brain_knowledge(id,brain_id,source_type,source_url,title,content,summary,keywords,relevance_score,learned_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                kid,
                brain_id,
                source_type,
                source_url,
                title[:260],
                content[:4000],
                summary[:900],
                keywords[:400],
                relevance_score,
                now_iso(),
            ),
        )
        return kid

    def init_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS ats_jobs(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT NOT NULL,
                department TEXT,
                location TEXT,
                description TEXT,
                urgency TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'open',
                ai_profile TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS ats_candidates(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                job_id TEXT,
                name TEXT NOT NULL,
                email TEXT,
                role TEXT,
                experience INTEGER DEFAULT 0,
                fit_score INTEGER DEFAULT 70,
                status TEXT DEFAULT 'applied',
                ai_strength TEXT,
                ai_concern TEXT,
                source TEXT DEFAULT 'manual',
                resume_text TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS network_connections(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                title TEXT,
                company TEXT,
                linkedin TEXT,
                notes TEXT,
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS network_posts(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                content TEXT NOT NULL,
                enhanced TEXT,
                kind TEXT DEFAULT 'post',
                likes INTEGER DEFAULT 0,
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS network_signals(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                query TEXT,
                analysis TEXT,
                carbon_mode TEXT DEFAULT 'graphene',
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS hq_clients(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                industry TEXT,
                value REAL DEFAULT 0,
                stage TEXT DEFAULT 'prospect',
                contact TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS hq_revenue(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                type TEXT DEFAULT 'revenue',
                amount REAL NOT NULL,
                source TEXT,
                category TEXT,
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS hq_team(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                name TEXT NOT NULL,
                role TEXT,
                email TEXT,
                department TEXT,
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS carbon_bonds(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                bond_type TEXT,
                source_system TEXT,
                target_system TEXT,
                protocol_mode TEXT DEFAULT 'graphene',
                signal TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS carbon_events(
                id TEXT PRIMARY KEY,
                event_type TEXT,
                payload TEXT,
                carbon_mode TEXT,
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS brain_knowledge(
                id TEXT PRIMARY KEY,
                brain_id TEXT NOT NULL,
                source_type TEXT,
                source_url TEXT,
                title TEXT,
                content TEXT,
                summary TEXT,
                keywords TEXT,
                relevance_score REAL DEFAULT 0.7,
                learned_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS media_library(
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                media_type TEXT,
                url TEXT,
                thumbnail TEXT,
                duration TEXT,
                source TEXT,
                added_at TEXT,
                play_count INTEGER DEFAULT 0,
                last_played TEXT
            )
            """
        )

    init_tables()

    @app.get("/media")
    async def media_page(request: Request):
        require_member(request)
        path = frontend_dir / "media.html"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Media page not found")
        return FileResponse(path)

    @app.get("/api/carbon/status")
    async def carbon_status(request: Request):
        require_master(request)
        state = get_state()
        bonds = db_all("SELECT * FROM carbon_bonds WHERE status='active' ORDER BY created_at DESC LIMIT 20") or []
        return {
            "modes": CARBON_MODES,
            "active_bonds": len(bonds),
            "bonds": bonds[:10],
            "events": carbon_events[-20:],
            "current_mode": state.get("settings", {}).get("carbon_mode", "graphene"),
            "identity": state.get("meta", {}).get("identity", core_identity),
        }

    @app.post("/api/carbon/bond")
    async def carbon_bond(req: CarbonBondReq, request: Request):
        user = require_master(request)
        result = await ai_text(
            (
                f"Explain the operational bond between {req.source_system} and {req.target_system}.\n"
                f"Bond type: {req.bond_type}\nMode: {req.protocol_mode}\nSignal: {req.signal}\n"
                "Return a concise operational analysis of what should flow, what must be protected, and the expected value."
            ),
            workspace="bridge",
            source="carbon",
            max_tokens=280,
        )
        bond_id = new_id("cbond")
        db_exec(
            """
            INSERT INTO carbon_bonds(id,user_id,bond_type,source_system,target_system,protocol_mode,signal,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (bond_id, user["id"], req.bond_type, req.source_system, req.target_system, req.protocol_mode, req.signal, "active", now_iso()),
        )
        emit_carbon("bond_formed", {"source": req.source_system, "target": req.target_system, "signal": req.signal}, req.protocol_mode)
        return {
            "id": bond_id,
            "bond": req.model_dump(),
            "analysis": result["text"],
            "provider": result["provider"],
            "mode": CARBON_MODES.get(req.protocol_mode, CARBON_MODES["graphene"]),
        }

    @app.post("/api/carbon/think")
    async def carbon_think(req: CarbonThinkReq, request: Request):
        require_master(request)
        mode_info = CARBON_MODES.get(req.mode, CARBON_MODES["graphene"])
        result = await ai_text(
            (
                f"Operate in {mode_info['name']} mode.\n"
                f"Mode description: {mode_info['desc']}\n"
                f"Best use: {mode_info['use']}\n\n"
                f"Problem: {req.problem}\n\n"
                "Return a structured response with: Focus, Observations, Action Plan."
            ),
            workspace="bridge",
            source="carbon",
            max_tokens=700,
            use_web_search=False,
        )
        emit_carbon("think", {"mode": req.mode, "problem": req.problem[:120]}, req.mode)
        return {"mode": req.mode, "mode_info": mode_info, "result": result["text"], "provider": result["provider"]}

    @app.get("/api/carbon/stream")
    async def carbon_stream(request: Request):
        async def gen():
            while True:
                if await request.is_disconnected():
                    break
                state = get_state()
                payload = {
                    "avatars": state.get("avatar_state", {}).get("active", ["RAMA"]),
                    "protection": state.get("avatar_state", {}).get("protection_meter", 100),
                    "guardian": state.get("meta", {}).get("memory_guardian", "eternal"),
                    "hunt_count": len(state.get("praapti_hunts", [])),
                    "proposals": len([p for p in state.get("nirmaan_proposals", []) if not p.get("approved")]),
                    "vault_size": len(state.get("vault", [])),
                    "carbon_events": carbon_events[-5:],
                    "carbon_mode": state.get("settings", {}).get("carbon_mode", "graphene"),
                    "identity": state.get("meta", {}).get("identity", core_identity),
                    "at": now_iso(),
                }
                blob = json.dumps(payload, ensure_ascii=False)
                yield f"event: snapshot\ndata: {blob}\n\n"
                yield f"data: {blob}\n\n"
                await asyncio.sleep(6)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/ats/state")
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

    @app.post("/api/ats/jobs")
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

    @app.post("/api/ats/candidates")
    async def ats_add_candidate(req: ATSCandidateReq, request: Request):
        user = require_master(request)
        result = await ai_text(
            (
                f"Evaluate this candidate for the role {req.role} at {company_name}.\n"
                f"Name: {req.name}\nExperience: {req.experience} years\nResume: {req.resume_text[:900] or 'Not provided'}\n"
                "Return strict JSON: {\"fit\": 82, \"strength\": \"...\", \"concern\": \"...\"}"
            ),
            workspace="ats",
            source="ats_candidate",
            max_tokens=180,
        )
        parsed = {}
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

    @app.put("/api/ats/candidates/{candidate_id}/move")
    async def ats_move_candidate(candidate_id: str, req: ATSMoveReq, request: Request):
        user = require_master(request)
        db_exec("UPDATE ats_candidates SET status=?, updated_at=? WHERE id=? AND user_id=?", (req.status, now_iso(), candidate_id, user["id"]))
        emit_carbon("candidate_moved", {"id": candidate_id, "status": req.status}, "nanotube")
        return {"ok": True, "id": candidate_id, "status": req.status}

    @app.delete("/api/ats/candidates/{candidate_id}")
    async def ats_delete_candidate(candidate_id: str, request: Request):
        user = require_master(request)
        db_exec("DELETE FROM ats_candidates WHERE id=? AND user_id=?", (candidate_id, user["id"]))
        return {"ok": True}

    @app.post("/api/ats/import-praapti")
    async def ats_import_praapti(request: Request):
        user = require_master(request)
        state = get_state()
        hunts = state.get("praapti_hunts", [])
        if not hunts:
            raise HTTPException(status_code=404, detail="No Praapti hunts found")
        hunt = hunts[-1]
        imported = []
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

    @app.post("/api/ats/ai-score-all")
    async def ats_ai_score_all(request: Request):
        user = require_master(request)
        candidates = db_all("SELECT * FROM ats_candidates WHERE user_id=? ORDER BY updated_at DESC LIMIT 25", (user["id"],)) or []
        updated = 0
        for cand in candidates:
            result = await ai_text(
                (
                    f"Quick fit score for candidate {cand['name']}.\n"
                    f"Role: {cand.get('role', '')}\nExperience: {cand.get('experience', 0)} years\n"
                    "Return strict JSON: {\"fit\": 78}"
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

    def safe_db_all(query: str, params=()) -> List[Dict[str, Any]]:
        try:
            return db_all(query, params) or []
        except Exception:
            return []

    def member_network_state_payload(viewer=None) -> Dict[str, Any]:
        user_id = (viewer or {}).get("id", "")
        user_email = ((viewer or {}).get("email") or "").strip().lower()
        connections = (
            safe_db_all("SELECT * FROM network_connections WHERE user_id=? ORDER BY created_at DESC LIMIT 24", (user_id,))
            if user_id
            else []
        )
        posts = (
            safe_db_all("SELECT * FROM network_posts WHERE user_id=? ORDER BY created_at DESC LIMIT 24", (user_id,))
            if user_id
            else []
        )
        openings = safe_db_all(
            """
            SELECT id,title,company_name,location,remote,job_type,experience_min,experience_max,skills,created_at
            FROM public_jobs
            WHERE lower(coalesce(status,''))='open'
            ORDER BY created_at DESC
            LIMIT 12
            """
        )
        companies = safe_db_all(
            """
            SELECT slug,name,tagline,website,city,plan,created_at
            FROM public_companies
            ORDER BY created_at DESC
            LIMIT 8
            """
        )
        profile = {}
        journeys = []
        next_move = ""
        if user_email:
            profile_rows = safe_db_all(
                "SELECT * FROM candidate_profiles WHERE lower(email)=lower(?) ORDER BY updated_at DESC LIMIT 1",
                (user_email,),
            )
            if profile_rows:
                profile = profile_rows[0]
                journeys = safe_db_all(
                    "SELECT * FROM candidate_job_journeys WHERE profile_id=? ORDER BY updated_at DESC LIMIT 10",
                    (profile["id"],),
                )
                applications = int(profile.get("applications_count") or 0)
                interviews = int(profile.get("interviews_count") or 0)
                offers = int(profile.get("offers_count") or 0)
                if offers:
                    next_move = "Protect the best offer, confirm joining intent, and close loose interview loops."
                elif interviews:
                    next_move = "Stay ready for feedback and keep at least two active backup pipelines open."
                elif applications:
                    next_move = "Follow up on submitted roles, sharpen the resume for gaps, and keep sourcing."
                elif (profile.get("job_change_intent") or "") in {"active", "passive"}:
                    next_move = "Open to change is active. Apply to matching jobs and keep recruiter conversations warm."
        stats = {
            "connections": len(connections),
            "posts": len(posts),
            "openings": len(openings),
            "companies": len(companies),
            "applications": int(profile.get("applications_count") or 0),
            "interviews": int(profile.get("interviews_count") or 0),
            "offers": int(profile.get("offers_count") or 0),
        }
        return {
            "auth": {
                "authenticated": bool(viewer),
                "role": (viewer or {}).get("role", "guest"),
            },
            "viewer": {
                "name": (viewer or {}).get("name", ""),
                "email": (viewer or {}).get("email", ""),
                "role": (viewer or {}).get("role", "guest"),
            },
            "profile": profile,
            "journeys": journeys,
            "next_move": next_move,
            "connections": connections,
            "posts": posts,
            "openings": openings,
            "companies": companies,
            "stats": stats,
            "summary": {
                "headline": "One professional network for candidates, recruiters, and live hiring demand.",
                "member_message": (
                    "Your posts, connections, resume profile, and job journey stay local to your workspace."
                    if viewer
                    else "Sign in to turn this network into your private candidate desk with ATS-linked job journeys."
                ),
            },
        }

    @app.get("/api/member-network/public-state")
    async def member_network_public_state():
        return member_network_state_payload(None)

    @app.get("/api/member-network/state")
    async def member_network_get_state(request: Request):
        user = require_member(request)
        return member_network_state_payload(user)

    @app.post("/api/member-network/connect")
    async def member_network_add_connection(req: NetworkConnReq, request: Request):
        user = require_member(request)
        connection_id = new_id("mconn")
        db_exec(
            """
            INSERT INTO network_connections(id,user_id,name,title,company,linkedin,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (connection_id, user["id"], req.name, req.title, req.company, req.linkedin, req.notes, now_iso()),
        )
        return {"ok": True, "id": connection_id}

    @app.delete("/api/member-network/connections/{connection_id}")
    async def member_network_delete_connection(connection_id: str, request: Request):
        user = require_member(request)
        db_exec("DELETE FROM network_connections WHERE id=? AND user_id=?", (connection_id, user["id"]))
        return {"ok": True}

    @app.post("/api/member-network/post")
    async def member_network_create_post(req: NetworkPostReq, request: Request):
        user = require_member(request)
        result = await ai_text(
            (
                "Enhance this professional network update for a candidate and recruiter audience.\n"
                f"Kind: {req.kind}\n"
                f"Original:\n{req.content}\n\n"
                "Keep it human, credible, and concise. Do not sound robotic."
            ),
            workspace="network",
            source="member_network_post",
            max_tokens=220,
        )
        post_id = new_id("mpost")
        enhanced = result["text"] or req.content
        db_exec(
            """
            INSERT INTO network_posts(id,user_id,content,enhanced,kind,likes,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (post_id, user["id"], req.content, enhanced, req.kind, 0, now_iso()),
        )
        return {"ok": True, "id": post_id, "enhanced": enhanced, "provider": result["provider"]}

    @app.post("/api/member-network/posts/{post_id}/like")
    async def member_network_like_post(post_id: str, request: Request):
        user = require_member(request)
        db_exec("UPDATE network_posts SET likes = likes + 1 WHERE id=? AND user_id=?", (post_id, user["id"]))
        return {"ok": True}

    @app.get("/api/network/state")
    async def network_get_state(request: Request):
        user = require_master(request)
        conns = db_all("SELECT * FROM network_connections WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        posts = db_all("SELECT * FROM network_posts WHERE user_id=? ORDER BY created_at DESC LIMIT 30", (user["id"],)) or []
        signals = db_all("SELECT * FROM network_signals WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user["id"],)) or []
        return {"connections": conns, "posts": posts, "signals": signals, "stats": {"connections": len(conns), "posts": len(posts), "signals": len(signals)}}

    @app.post("/api/network/connect")
    async def network_add_connection(req: NetworkConnReq, request: Request):
        user = require_master(request)
        connection_id = new_id("conn")
        db_exec(
            """
            INSERT INTO network_connections(id,user_id,name,title,company,linkedin,notes,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (connection_id, user["id"], req.name, req.title, req.company, req.linkedin, req.notes, now_iso()),
        )
        emit_carbon("connection_added", {"name": req.name, "company": req.company}, "graphene")
        return {"ok": True, "id": connection_id}

    @app.delete("/api/network/connections/{connection_id}")
    async def network_delete_connection(connection_id: str, request: Request):
        user = require_master(request)
        db_exec("DELETE FROM network_connections WHERE id=? AND user_id=?", (connection_id, user["id"]))
        return {"ok": True}

    @app.post("/api/network/post")
    async def network_create_post(req: NetworkPostReq, request: Request):
        user = require_master(request)
        result = await ai_text(
            (
                f"Enhance this professional TechBuzz post for LinkedIn.\n"
                f"Kind: {req.kind}\nOriginal:\n{req.content}\n\n"
                "Keep it concise, specific, and credible."
            ),
            workspace="network",
            source="network_post",
            max_tokens=260,
        )
        post_id = new_id("post")
        enhanced = result["text"] or req.content
        db_exec(
            """
            INSERT INTO network_posts(id,user_id,content,enhanced,kind,likes,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (post_id, user["id"], req.content, enhanced, req.kind, 0, now_iso()),
        )
        emit_carbon("post_created", {"kind": req.kind}, "graphene")
        return {"ok": True, "id": post_id, "enhanced": enhanced, "provider": result["provider"]}

    @app.post("/api/network/signal")
    async def network_signal_scan(req: NetworkSignalReq, request: Request):
        user = require_master(request)
        mode_info = CARBON_MODES.get(req.mode, CARBON_MODES["graphene"])
        query_lower = (req.query or "").strip().lower()
        short_signal = any(term in query_lower for term in ("one line", "short line", "keep it short", "one short sentence"))
        result = await ai_text(
            (
                f"Analyze this market signal for {company_name}.\n"
                f"Mode: {mode_info['name']} - {mode_info['desc']}\n"
                f"Query: {req.query}\n"
                + (
                    "Return one short human line with the clearest market signal and the next move."
                    if short_signal
                    else "Return 4 concrete findings: talent market, pricing, competitor motion, opportunity."
                )
            ),
            workspace="network",
            source="network_signal",
            max_tokens=90 if short_signal else 520,
            use_web_search=True,
        )
        signal_id = new_id("sig")
        db_exec(
            """
            INSERT INTO network_signals(id,user_id,query,analysis,carbon_mode,created_at)
            VALUES(?,?,?,?,?,?)
            """,
            (signal_id, user["id"], req.query, result["text"], req.mode, now_iso()),
        )
        emit_carbon("signal_scan", {"query": req.query, "mode": req.mode}, req.mode)
        return {
            "ok": True,
            "id": signal_id,
            "query": req.query,
            "analysis": result["text"],
            "mode": req.mode,
            "mode_info": mode_info,
            "provider": result["provider"],
        }

    @app.post("/api/network/posts/{post_id}/like")
    async def network_like_post(post_id: str, request: Request):
        user = require_master(request)
        db_exec("UPDATE network_posts SET likes = likes + 1 WHERE id=? AND user_id=?", (post_id, user["id"]))
        return {"ok": True}

    @app.get("/api/hq/state")
    async def hq_get_state(request: Request):
        user = require_master(request)
        clients = db_all("SELECT * FROM hq_clients WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        revenue = db_all("SELECT * FROM hq_revenue WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        team = db_all("SELECT * FROM hq_team WHERE user_id=? ORDER BY created_at DESC", (user["id"],)) or []
        total_revenue = sum(float(item.get("amount", 0) or 0) for item in revenue if item.get("type") == "revenue")
        total_expenses = sum(float(item.get("amount", 0) or 0) for item in revenue if item.get("type") == "expense")
        state = get_state()
        insight_result = await ai_text(
            (
                f"Give a sharp 2-sentence strategic insight for {company_name}.\n"
                f"Clients: {len(clients)}\nTeam: {len(team)}\nRevenue: ₹{total_revenue:,.0f}\n"
                f"Praapti hunts: {len(state.get('praapti_hunts', []))}\n"
                "Focus on today's highest-leverage move."
            ),
            workspace="hq",
            source="hq_insight",
            max_tokens=140,
        )
        return {
            "clients": clients,
            "revenue": revenue,
            "team": team,
            "metrics": {
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "net_profit": total_revenue - total_expenses,
                "active_clients": len([c for c in clients if c.get("stage") == "active"]),
                "prospects": len([c for c in clients if c.get("stage") == "prospect"]),
                "won": len([c for c in clients if c.get("stage") == "closed_won"]),
                "team_size": len(team),
                "praapti_hunts": len(state.get("praapti_hunts", [])),
                "vault_items": len(state.get("vault", [])),
            },
            "ai_insight": insight_result["text"],
            "carbon_mode": get_state().get("settings", {}).get("carbon_mode", "graphene"),
            "provider": insight_result["provider"],
        }

    @app.post("/api/hq/clients")
    async def hq_add_client(req: HQClientReq, request: Request):
        user = require_master(request)
        client_id = new_id("cl")
        db_exec(
            """
            INSERT INTO hq_clients(id,user_id,name,industry,value,stage,contact,notes,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (client_id, user["id"], req.name, req.industry, req.value, req.stage, req.contact, req.notes, now_iso(), now_iso()),
        )
        emit_carbon("client_added", {"name": req.name, "stage": req.stage}, "nanotube")
        return {"ok": True, "id": client_id}

    @app.put("/api/hq/clients/{client_id}/stage")
    async def hq_move_client(client_id: str, req: HQClientMoveReq, request: Request):
        user = require_master(request)
        db_exec("UPDATE hq_clients SET stage=?, updated_at=? WHERE id=? AND user_id=?", (req.stage, now_iso(), client_id, user["id"]))
        emit_carbon("client_moved", {"id": client_id, "stage": req.stage}, "nanotube")
        return {"ok": True}

    @app.delete("/api/hq/clients/{client_id}")
    async def hq_delete_client(client_id: str, request: Request):
        user = require_master(request)
        db_exec("DELETE FROM hq_clients WHERE id=? AND user_id=?", (client_id, user["id"]))
        return {"ok": True}

    @app.post("/api/hq/revenue")
    async def hq_add_revenue(req: HQRevenueReq, request: Request):
        user = require_master(request)
        revenue_id = new_id("rev")
        db_exec(
            """
            INSERT INTO hq_revenue(id,user_id,type,amount,source,category,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (revenue_id, user["id"], req.type, req.amount, req.source, req.category, now_iso()),
        )
        emit_carbon("revenue_entry", {"type": req.type, "amount": req.amount}, "nanotube")
        return {"ok": True, "id": revenue_id}

    @app.post("/api/hq/team")
    async def hq_add_team(req: HQTeamReq, request: Request):
        user = require_master(request)
        team_id = new_id("tm")
        db_exec(
            """
            INSERT INTO hq_team(id,user_id,name,role,email,department,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (team_id, user["id"], req.name, req.role, req.email, req.department, now_iso()),
        )
        return {"ok": True, "id": team_id}

    @app.delete("/api/hq/team/{team_id}")
    async def hq_delete_team(team_id: str, request: Request):
        user = require_master(request)
        db_exec("DELETE FROM hq_team WHERE id=? AND user_id=?", (team_id, user["id"]))
        return {"ok": True}

    @app.post("/api/hq/strategy")
    async def hq_strategy(request: Request):
        user = require_master(request)
        body = await request.json()
        goal = body.get("goal", "Grow TechBuzz revenue")
        mode = body.get("mode", "diamond")
        mode_info = CARBON_MODES.get(mode, CARBON_MODES["diamond"])
        revenue = db_all("SELECT * FROM hq_revenue WHERE user_id=?", (user["id"],)) or []
        clients = db_all("SELECT * FROM hq_clients WHERE user_id=?", (user["id"],)) or []
        total_revenue = sum(float(item.get("amount", 0) or 0) for item in revenue if item.get("type") == "revenue")
        result = await ai_text(
            (
                f"Operate in {mode_info['name']} mode.\n"
                f"Goal: {goal}\n"
                f"Active clients: {len([c for c in clients if c.get('stage') == 'active'])}\n"
                f"Total revenue: ₹{total_revenue:,.0f}\n"
                "Provide sections: Immediate Actions, Growth Levers, Risks, Next 7 Days."
            ),
            workspace="hq",
            source="hq_strategy",
            max_tokens=780,
            use_web_search=False,
        )
        emit_carbon("strategy_run", {"goal": goal[:100], "mode": mode}, mode)
        return {"result": result["text"], "mode": mode, "mode_info": mode_info, "provider": result["provider"]}

    @app.get("/api/voice/profile")
    async def voice_profile(request: Request):
        require_member(request)
        state = get_state()
        voice = state.get("voice", {})
        return {
            "language": voice.get("language", "en-IN"),
            "rate": voice.get("rate", 0.94),
            "pitch": voice.get("pitch", 1.08),
            "profile": voice.get("voice_profile", "sovereign_female"),
            "wake_words": voice.get("wake_words", ["hey jinn", "my king commands"]),
            "always_listening": voice.get("always_listening", False),
        }

    @app.post("/api/intel/search")
    async def intel_search(req: IntelSearchReq, request: Request):
        require_master(request)
        results = await ddg_search(req.query)
        stored = []
        for item in results:
            kid = store_brain_knowledge(req.brain_id, "web_search", item["title"], item["url"], item["snippet"], item["snippet"], req.query, 0.72)
            stored.append({**item, "id": kid})
        emit_carbon("intel_search", {"brain_id": req.brain_id, "query": req.query, "count": len(stored)}, "graphene")
        return {"ok": True, "brain_id": req.brain_id, "query": req.query, "stored": len(stored), "results": stored}

    @app.post("/api/intel/news")
    async def intel_news(req: IntelNewsReq, request: Request):
        require_master(request)
        items: List[Dict[str, str]] = []
        for feed in NEWS_FEEDS.get(req.category, NEWS_FEEDS["tech"])[:2]:
            items.extend(await fetch_rss_items(feed, limit=4))
        stored = []
        for item in items[:8]:
            kid = store_brain_knowledge(req.brain_id, "news_feed", item["title"], item["url"], item["snippet"], item["snippet"], req.category, 0.75)
            stored.append({**item, "id": kid})
        emit_carbon("intel_news", {"brain_id": req.brain_id, "category": req.category, "count": len(stored)}, "graphene")
        return {"ok": True, "brain_id": req.brain_id, "category": req.category, "stored": len(stored), "results": stored}

    @app.post("/api/intel/fetch-url")
    async def intel_fetch_url(req: IntelFetchReq, request: Request):
        require_master(request)
        content = await fetch_url_text(req.url)
        kid = store_brain_knowledge(req.brain_id, "url_fetch", f"Fetched: {req.url[:80]}", req.url, content, content[:400], "url_fetch", 0.8)
        emit_carbon("url_fetched", {"brain_id": req.brain_id, "url": req.url[:100]}, "nanotube")
        return {"ok": True, "brain_id": req.brain_id, "url": req.url, "id": kid, "content_length": len(content), "preview": content[:400]}

    @app.get("/api/intel/knowledge/{brain_id}")
    async def get_brain_knowledge(brain_id: str, request: Request):
        require_master(request)
        rows = db_all("SELECT * FROM brain_knowledge WHERE brain_id=? ORDER BY learned_at DESC LIMIT 20", (brain_id,)) or []
        return {"brain_id": brain_id, "brain_name": brain_id.replace("_", " "), "knowledge": rows, "total_learned": len(rows), "learning_score": min(0.99, 0.4 + len(rows) * 0.03)}

    @app.get("/api/intel/all-knowledge")
    async def get_all_knowledge(request: Request):
        require_master(request)
        rows = db_all("SELECT * FROM brain_knowledge ORDER BY learned_at DESC LIMIT 50") or []
        return {"knowledge": rows, "total": len(rows)}

    @app.post("/api/intel/mass-learn")
    async def intel_mass_learn(request: Request):
        require_master(request)
        learn_map = {
            "sec_signals": ("tech hiring trends India", "web"),
            "sec_anveshan": ("artificial intelligence latest research", "web"),
            "sec_hunt": ("passive candidate sourcing techniques", "web"),
            "exec_research": ("tech", "news"),
            "exec_accounts": ("india_business", "news"),
            "dom_network": ("India startup ecosystem", "web"),
        }
        results: Dict[str, int] = {}
        for brain_id, (topic, mode) in learn_map.items():
            try:
                if mode == "news":
                    items = []
                    for feed in NEWS_FEEDS.get(topic, NEWS_FEEDS["tech"])[:1]:
                        items.extend(await fetch_rss_items(feed, limit=3))
                    for item in items:
                        store_brain_knowledge(brain_id, "news_feed", item["title"], item["url"], item["snippet"], item["snippet"], topic, 0.74)
                    results[brain_id] = len(items)
                else:
                    items = await ddg_search(topic)
                    for item in items:
                        store_brain_knowledge(brain_id, "web_search", item["title"], item["url"], item["snippet"], item["snippet"], topic, 0.71)
                    results[brain_id] = len(items)
            except Exception as exc:
                log.debug("Mass learn failed for %s: %s", brain_id, exc)
                results[brain_id] = 0
        emit_carbon("mass_learn_complete", {"brains": len(results), "total": sum(results.values())}, "graphene")
        return {"ok": True, "results": results, "total_learned": sum(results.values())}

    @app.get("/api/intel/sources")
    async def intel_get_sources(request: Request):
        require_master(request)
        return {
            "news_feeds": NEWS_FEEDS,
            "feed_count": sum(len(v) for v in NEWS_FEEDS.values()),
            "search_engine": "DuckDuckGo HTML",
            "web_scraping": "httpx + regex cleanup",
        }

    @app.post("/api/media/save")
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

    @app.get("/api/media/library")
    async def media_library(request: Request):
        user = require_member(request)
        items = db_all("SELECT * FROM media_library WHERE user_id=? ORDER BY added_at DESC LIMIT 40", (user["id"],)) or []
        return {"items": items, "total": len(items)}

    @app.put("/api/media/play/{media_id}")
    async def media_play_count(media_id: str, request: Request):
        user = require_member(request)
        db_exec("UPDATE media_library SET play_count=play_count+1,last_played=? WHERE id=? AND user_id=?", (now_iso(), media_id, user["id"]))
        return {"ok": True}
