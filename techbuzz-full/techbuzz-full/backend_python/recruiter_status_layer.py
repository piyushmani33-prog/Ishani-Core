"""
Recruiter Status Layer
======================
Lightweight endpoints for the Recruiter Product Mode page.
Provides quick stats, status generation (summary/sheet), and
platform-specific formatting helpers.

All data is scoped to the authenticated user.  SQL uses
parameterised queries throughout.
"""

from __future__ import annotations

import json
from datetime import datetime, UTC
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    mode: str = "sheet"          # "summary" | "sheet"
    format: str = "plain_text"   # "plain_text" | "tsv" | "csv"
    date_from: str = ""
    date_to: str = ""


class FormatForShareRequest(BaseModel):
    output: str = ""
    target: str = "plain"        # "teams" | "whatsapp" | "email" | "plain"


class TrackerAddRequest(BaseModel):
    candidate_name: str = ""
    position: str = ""
    process_stage: str = "sourced"
    response_status: str = "pending_review"
    remarks: str = ""
    row_id: str = ""             # if set → update existing row


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_str() -> str:
    return datetime.now(UTC).strftime("%d %b %Y")


def _iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Sheet generation helpers
# ---------------------------------------------------------------------------

_STAGE_MAP: Dict[str, str] = {
    "sourced": "sourced",
    "screening": "shortlisted",
    "interview": "interviews",
    "offer": "offers",
    "hired": "closures",
    "closed": "closures",
}


def _aggregate_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group tracker rows by position and count pipeline stages."""
    buckets: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        pos = (row.get("position") or "Unknown").strip() or "Unknown"
        if pos not in buckets:
            buckets[pos] = {
                "role": pos,
                "sourced": 0,
                "shortlisted": 0,
                "interviews": 0,
                "offers": 0,
                "closures": 0,
                "remarks_list": [],
            }
        stage_raw = (row.get("process_stage") or "sourced").lower()
        col = _STAGE_MAP.get(stage_raw, "sourced")
        buckets[pos][col] += 1
        remark = (row.get("remarks") or "").strip()
        if remark and remark not in buckets[pos]["remarks_list"]:
            buckets[pos]["remarks_list"].append(remark)

    results = []
    for b in buckets.values():
        b["notes"] = "; ".join(b.pop("remarks_list", []))[:120] or "-"
        results.append(b)
    return results


def _format_plain_text(aggregated: List[Dict[str, Any]]) -> str:
    lines = [f"📊 Recruiter Status — {_today_str()}", ""]
    for r in aggregated:
        lines.append(f"Role: {r['role']}")
        lines.append(
            f"  Sourced: {r['sourced']} | Shortlisted: {r['shortlisted']} | "
            f"Interviews: {r['interviews']} | Offers: {r['offers']} | "
            f"Closures: {r['closures']} | Notes: {r['notes']}"
        )
        lines.append("")
    return "\n".join(lines).rstrip()


def _format_tsv(aggregated: List[Dict[str, Any]]) -> str:
    header = "Role\tProfiles Sourced\tShortlisted\tInterviews Scheduled\tOffers\tClosures\tNotes"
    rows = [
        f"{r['role']}\t{r['sourced']}\t{r['shortlisted']}\t{r['interviews']}\t{r['offers']}\t{r['closures']}\t{r['notes']}"
        for r in aggregated
    ]
    return "\n".join([header] + rows)


def _format_csv(aggregated: List[Dict[str, Any]]) -> str:
    def _esc(v: str) -> str:
        if "," in v or '"' in v:
            return '"' + v.replace('"', '""') + '"'
        return v

    header = "Role,Profiles Sourced,Shortlisted,Interviews Scheduled,Offers,Closures,Notes"
    rows = [
        ",".join([
            _esc(r["role"]),
            str(r["sourced"]),
            str(r["shortlisted"]),
            str(r["interviews"]),
            str(r["offers"]),
            str(r["closures"]),
            _esc(r["notes"]),
        ])
        for r in aggregated
    ]
    return "\n".join([header] + rows)


# ---------------------------------------------------------------------------
# Share formatters
# ---------------------------------------------------------------------------

def _format_teams(raw: str) -> str:
    lines = [l for l in raw.splitlines() if l.strip()]
    md_lines = ["**📊 Recruiter Status Update**", ""]
    header = "| Role | Sourced | Shortlisted | Interviews | Offers | Closures |"
    sep    = "|------|---------|-------------|------------|--------|----------|"
    data_rows: List[str] = []

    for line in lines:
        # Try to parse data lines from plain-text output  ("Role: X\n  Sourced: …")
        if line.startswith("Role:"):
            role = line.split(":", 1)[1].strip()
            data_rows.append(role)
        elif "Sourced:" in line and "|" in line:
            parts = dict(
                p.strip().split(":", 1)
                for p in line.split("|")
                if ":" in p
            )
            role = data_rows[-1] if data_rows else "—"
            md_lines_row = "| {} | {} | {} | {} | {} | {} |".format(
                role,
                parts.get("Sourced", "-").strip(),
                parts.get("Shortlisted", "-").strip(),
                parts.get("Interviews", "-").strip(),
                parts.get("Offers", "-").strip(),
                parts.get("Closures", "-").strip(),
            )
            if header not in md_lines:
                md_lines += [header, sep]
            md_lines.append(md_lines_row)
        else:
            if not any(l.startswith("|") for l in md_lines):
                md_lines.append(line)

    if not any(l.startswith("|") for l in md_lines):
        md_lines += ["", "```", raw, "```"]

    return "\n".join(md_lines)


def _format_whatsapp(raw: str) -> str:
    lines = raw.splitlines()
    wa_lines = ["📊 *Recruiter Status Update*", ""]
    role = ""
    stats: Dict[str, str] = {}

    for line in lines:
        line = line.strip()
        if not line:
            if role and stats:
                wa_lines.append(f"🔹 *{role}*")
                wa_lines.append(
                    f"✅ Sourced: {stats.get('Sourced', '0')} | Shortlisted: {stats.get('Shortlisted', '0')}"
                )
                wa_lines.append(
                    f"📞 Interviews: {stats.get('Interviews', '0')} | 🎯 Offers: {stats.get('Offers', '0')}"
                )
                if stats.get("Notes", "-") != "-":
                    wa_lines.append(f"📝 Notes: {stats['Notes']}")
                wa_lines.append("")
                role, stats = "", {}
            continue

        if line.startswith("Role:"):
            role = line.split(":", 1)[1].strip()
        elif "Sourced:" in line and "|" in line:
            for part in line.split("|"):
                part = part.strip()
                if ":" in part:
                    k, v = part.split(":", 1)
                    stats[k.strip()] = v.strip()
        elif line.startswith("📊"):
            continue
        elif not role:
            wa_lines.append(line)

    # flush last role
    if role and stats:
        wa_lines.append(f"🔹 *{role}*")
        wa_lines.append(
            f"✅ Sourced: {stats.get('Sourced', '0')} | Shortlisted: {stats.get('Shortlisted', '0')}"
        )
        wa_lines.append(
            f"📞 Interviews: {stats.get('Interviews', '0')} | 🎯 Offers: {stats.get('Offers', '0')}"
        )
        if stats.get("Notes", "-") != "-":
            wa_lines.append(f"📝 Notes: {stats['Notes']}")

    if len(wa_lines) <= 2:
        wa_lines += ["", raw]

    return "\n".join(wa_lines)


def _format_email(raw: str) -> str:
    return (
        f"Hi,\n\nPlease find today's recruitment status update below.\n\n"
        f"{raw}\n\nBest regards"
    )


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def register_recruiter_status_routes(
    app,
    *,
    db_all: Callable,
    db_one: Callable,
    db_exec: Callable,
    new_id: Callable,
    now_iso: Callable,
    session_user: Callable,
    generate_text: Optional[Callable] = None,
    log=None,
) -> None:
    """Register all /api/recruiter-status/* routes onto *app*."""

    # ------------------------------------------------------------------
    # GET /api/recruiter-status/quick-stats
    # ------------------------------------------------------------------
    @app.get("/api/recruiter-status/quick-stats")
    async def recruiter_quick_stats(request: Request):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        uid = user["id"]

        total_rows = db_one(
            "SELECT COUNT(*) AS n FROM recruitment_tracker_rows WHERE user_id=?",
            (uid,),
        ) or {}

        interviews = db_one(
            "SELECT COUNT(*) AS n FROM recruitment_tracker_rows "
            "WHERE user_id=? AND process_stage='interview'",
            (uid,),
        ) or {}

        offers = db_one(
            "SELECT COUNT(*) AS n FROM recruitment_tracker_rows "
            "WHERE user_id=? AND process_stage='offer'",
            (uid,),
        ) or {}

        closures = db_one(
            "SELECT COUNT(*) AS n FROM recruitment_tracker_rows "
            "WHERE user_id=? AND process_stage IN ('hired','closed')",
            (uid,),
        ) or {}

        today_pfx = datetime.now(UTC).strftime("%Y-%m-%d")
        today_updated = db_one(
            "SELECT COUNT(*) AS n FROM recruitment_tracker_rows "
            "WHERE user_id=? AND updated_at LIKE ?",
            (uid, f"{today_pfx}%"),
        ) or {}

        return {
            "total_rows": _safe_int(total_rows.get("n")),
            "today_updated": _safe_int(today_updated.get("n")),
            "interviews_scheduled": _safe_int(interviews.get("n")),
            "offers": _safe_int(offers.get("n")),
            "closures": _safe_int(closures.get("n")),
        }

    # ------------------------------------------------------------------
    # POST /api/recruiter-status/generate
    # ------------------------------------------------------------------
    @app.post("/api/recruiter-status/generate")
    async def recruiter_generate_status(request: Request, body: GenerateRequest):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        uid = user["id"]
        mode = body.mode.lower()
        fmt = body.format.lower()

        rows = db_all(
            "SELECT * FROM recruitment_tracker_rows WHERE user_id=? ORDER BY updated_at DESC",
            (uid,),
        )

        if mode == "summary":
            # AI-based summary
            if not rows:
                return {
                    "output": "No tracker data found. Add some candidates first.",
                    "format": "plain_text",
                    "mode": "summary",
                    "row_count": 0,
                    "generated_at": _iso(),
                }

            # Build a compact context string
            snippets = []
            for r in rows[:30]:
                snippets.append(
                    f"- {r.get('candidate_name','?')} | {r.get('position','?')} | "
                    f"{r.get('process_stage','?')} | {r.get('response_status','?')}"
                )
            context = "\n".join(snippets)
            prompt = (
                "Generate a brief, professional recruitment status summary "
                "for a manager covering today's tracker activity. Be concise (under 200 words). "
                "Use bullet points.\n\nTracker data:\n" + context
            )
            system_prompt = (
                "You are a recruitment analyst assistant. Provide concise, professional "
                "summaries suitable for management reporting."
            )

            output = ""
            if generate_text:
                try:
                    result = await generate_text(
                        prompt,
                        system=system_prompt,
                        max_tokens=400,
                        source="recruiter_status",
                    )
                    output = result.get("text", "") if isinstance(result, dict) else str(result)
                except Exception as exc:
                    if log:
                        log.warning("recruiter_status summary AI error: %s", exc)

            if not output:
                # Fallback: plain text summary without AI
                agg = _aggregate_rows(rows)
                output = _format_plain_text(agg)

            return {
                "output": output,
                "format": "plain_text",
                "mode": "summary",
                "row_count": len(rows),
                "generated_at": _iso(),
            }

        # sheet mode (default)
        agg = _aggregate_rows(rows)

        if fmt == "tsv":
            output = _format_tsv(agg)
        elif fmt == "csv":
            output = _format_csv(agg)
        else:
            output = _format_plain_text(agg)

        return {
            "output": output,
            "format": fmt,
            "mode": "sheet",
            "row_count": len(rows),
            "generated_at": _iso(),
        }

    # ------------------------------------------------------------------
    # POST /api/recruiter-status/format-for-share
    # ------------------------------------------------------------------
    @app.post("/api/recruiter-status/format-for-share")
    async def recruiter_format_for_share(request: Request, body: FormatForShareRequest):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        raw = body.output or ""
        target = (body.target or "plain").lower()

        if target == "teams":
            formatted = _format_teams(raw)
        elif target == "whatsapp":
            formatted = _format_whatsapp(raw)
        elif target == "email":
            formatted = _format_email(raw)
        else:
            formatted = raw

        return {"formatted": formatted, "target": target}

    # ------------------------------------------------------------------
    # POST /api/recruiter-status/tracker-add
    # Quick add/update a single tracker row from the Recruiter Mode page
    # ------------------------------------------------------------------
    @app.post("/api/recruiter-status/tracker-add")
    async def recruiter_tracker_add(request: Request, body: TrackerAddRequest):
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        uid = user["id"]
        ts = now_iso()

        if body.row_id:
            # Update existing row — verify ownership first
            existing = db_one(
                "SELECT id FROM recruitment_tracker_rows WHERE id=? AND user_id=?",
                (body.row_id, uid),
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Row not found")
            db_exec(
                "UPDATE recruitment_tracker_rows "
                "SET candidate_name=?, position=?, process_stage=?, response_status=?, remarks=?, updated_at=? "
                "WHERE id=? AND user_id=?",
                (
                    body.candidate_name,
                    body.position,
                    body.process_stage,
                    body.response_status,
                    body.remarks,
                    ts,
                    body.row_id,
                    uid,
                ),
            )
            return {"ok": True, "action": "updated", "id": body.row_id}

        # Insert new row
        rid = new_id("rt")
        db_exec(
            "INSERT INTO recruitment_tracker_rows "
            "(id, user_id, candidate_name, position, process_stage, response_status, remarks, "
            "submission_state, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,'draft',?,?)",
            (
                rid,
                uid,
                body.candidate_name,
                body.position,
                body.process_stage,
                body.response_status,
                body.remarks,
                ts,
                ts,
            ),
        )
        return {"ok": True, "action": "created", "id": rid}
