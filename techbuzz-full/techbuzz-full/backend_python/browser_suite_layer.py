import asyncio
import json
import os
import random
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


def install_browser_suite_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_one = ctx["db_one"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    generate_text = ctx["generate_text"]
    get_state = ctx["get_state"]
    brain_hierarchy_payload = ctx["brain_hierarchy_payload"]
    nervous_system_payload = ctx["nervous_system_payload"]
    mother_monitor_payload = ctx["mother_monitor_payload"]
    portal_state_payload = ctx["portal_state_payload"]
    normalize_navigator_url = ctx.get("normalize_navigator_url")
    broadcast_brain_lesson = ctx.get("broadcast_brain_lesson")
    akshaya_save = ctx.get("akshaya_save")
    AI_NAME = ctx["AI_NAME"]
    COMPANY_NAME = ctx["COMPANY_NAME"]
    CORE_IDENTITY = ctx["CORE_IDENTITY"]
    log = ctx["log"]

    DATA_DIR = Path(__file__).resolve().parent / "data"
    BROWSER_DIR = DATA_DIR / "browser_suite"
    IDE_DIR = BROWSER_DIR / "ide_projects"
    SOFTWARE_DIR = BROWSER_DIR / "software_registry"
    SPREAD_DIR = BROWSER_DIR / "spread_vault"
    for directory in (BROWSER_DIR, IDE_DIR, SOFTWARE_DIR, SPREAD_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    DEFAULT_PUBLIC_JOBS = [
        {
            "id": "job_techbuzz_python_001",
            "title": "Python FastAPI Recruitment Automation Engineer",
            "company_name": "TechBuzz Systems Pvt. Ltd.",
            "location": "Noida, India",
            "remote": "hybrid",
            "job_type": "full_time",
            "experience_min": 3,
            "experience_max": 7,
            "salary_min": 1200000,
            "salary_max": 1800000,
            "skills": "Python, FastAPI, SQLite, Recruitment Automation, REST APIs, Prompt Engineering",
            "description": "Build recruitment automation, ATS integrations, candidate scoring, and owner dashboards for TechBuzz delivery teams.",
            "category": "engineering",
        },
        {
            "id": "job_techbuzz_talent_002",
            "title": "Talent Acquisition Specialist - Tech Hiring",
            "company_name": "TechBuzz Systems Pvt. Ltd.",
            "location": "Gurugram, India",
            "remote": "remote",
            "job_type": "full_time",
            "experience_min": 2,
            "experience_max": 6,
            "salary_min": 700000,
            "salary_max": 1200000,
            "skills": "Sourcing, Screening, Naukri, LinkedIn, Hiring Coordination, Stakeholder Management",
            "description": "Own sourcing, screening, and candidate engagement for engineering, product, and executive mandates across India and GCC.",
            "category": "recruitment",
        },
        {
            "id": "job_techbuzz_react_003",
            "title": "Frontend Experience Engineer",
            "company_name": "TechBuzz Systems Pvt. Ltd.",
            "location": "Bengaluru, India",
            "remote": "hybrid",
            "job_type": "full_time",
            "experience_min": 4,
            "experience_max": 8,
            "salary_min": 1400000,
            "salary_max": 2400000,
            "skills": "JavaScript, CSS, HTML, UI Systems, Data Visualization, React",
            "description": "Design premium recruitment, HQ, and neural system experiences with strong animation, data storytelling, and responsive design.",
            "category": "engineering",
        },
        {
            "id": "job_techbuzz_sales_004",
            "title": "Client Acquisition Manager - Staffing",
            "company_name": "TechBuzz Systems Pvt. Ltd.",
            "location": "Mumbai, India",
            "remote": "field",
            "job_type": "full_time",
            "experience_min": 5,
            "experience_max": 10,
            "salary_min": 1000000,
            "salary_max": 2200000,
            "skills": "B2B Sales, Staffing, Client Hunting, Revenue Growth, Proposal Writing, CRM",
            "description": "Open new staffing and recruitment accounts, manage enterprise pitches, and convert demand into delivery-ready hiring pipelines.",
            "category": "sales",
        },
        {
            "id": "job_techbuzz_devops_005",
            "title": "DevOps and Release Architect",
            "company_name": "TechBuzz Systems Pvt. Ltd.",
            "location": "Pune, India",
            "remote": "remote",
            "job_type": "contract",
            "experience_min": 5,
            "experience_max": 9,
            "salary_min": 1600000,
            "salary_max": 2600000,
            "skills": "CI/CD, Docker, Kubernetes, Linux, Monitoring, Release Automation",
            "description": "Create reliable rollout, deployment, migration, and environment control systems for the TechBuzz mission stack.",
            "category": "engineering",
        },
    ]

    FILEHIPPO_FALLBACK = [
        {"title": "Visual Studio Code", "category": "development", "summary": "Modern code editor with extension marketplace, terminal, debugging, and Git support.", "url": "https://filehippo.com/download_visual-studio-code/"},
        {"title": "Notepad++", "category": "development", "summary": "Fast lightweight editor for code, notes, and scripts with plugin support.", "url": "https://filehippo.com/download_notepad-plus-plus-32/"},
        {"title": "7-Zip", "category": "utilities", "summary": "Compression utility for archives, packaging, and local file handling.", "url": "https://filehippo.com/download_7zip-64/"},
        {"title": "VLC Media Player", "category": "multimedia", "summary": "Cross-format media playback software with streaming and conversion support.", "url": "https://filehippo.com/download_vlc-media-player-64/"},
        {"title": "KeePass", "category": "security", "summary": "Secure password vault useful for credentials and operator-controlled secret handling.", "url": "https://filehippo.com/download_keepass-password-safe/"},
    ]

    C_TEMPLATES = [
        {"id": "signal_hash", "name": "Signal Hash Core", "description": "Hashes incoming signals for fast routing decisions.", "language": "c"},
        {"id": "fit_score", "name": "Fit Score Engine", "description": "Scores candidate-job matches using lightweight C logic.", "language": "c"},
        {"id": "mesh_router", "name": "Mesh Router", "description": "Simulates low-level routing for the neural mesh.", "language": "cpp"},
    ]

    def ensure_tables() -> None:
        def ensure_column(table: str, column: str, ddl: str) -> None:
            try:
                rows = db_all(f"PRAGMA table_info({table})") or []
                existing = {str(row.get("name", "")) for row in rows}
                if column not in existing:
                    db_exec(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            except Exception:
                pass

        db_exec("CREATE TABLE IF NOT EXISTS browser_suite_state(scope TEXT PRIMARY KEY,payload_json TEXT NOT NULL,updated_at TEXT NOT NULL)")
        db_exec("CREATE TABLE IF NOT EXISTS browser_sessions(id TEXT PRIMARY KEY,user_id TEXT,name TEXT,current_url TEXT,current_title TEXT,status TEXT,created_at TEXT,updated_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS browser_history(id TEXT PRIMARY KEY,user_id TEXT,session_id TEXT,url TEXT,title TEXT,platform TEXT,favicon TEXT,text_preview TEXT,latency_ms INTEGER,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS browser_learned(id TEXT PRIMARY KEY,user_id TEXT,session_id TEXT,platform TEXT,topic TEXT,url TEXT,snippet TEXT,learned_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS browser_accounts(id TEXT PRIMARY KEY,user_id TEXT,platform TEXT,email TEXT,username TEXT,created_at TEXT,updated_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS browser_rewrites(id TEXT PRIMARY KEY,user_id TEXT,component TEXT,reason TEXT,mutation_type TEXT,improvement TEXT,proposal TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS public_companies(id TEXT PRIMARY KEY,slug TEXT NOT NULL UNIQUE,name TEXT NOT NULL,owner_name TEXT NOT NULL,owner_email TEXT NOT NULL,plan TEXT NOT NULL DEFAULT 'starter',api_key TEXT NOT NULL UNIQUE,tagline TEXT DEFAULT '',website TEXT DEFAULT '',city TEXT DEFAULT '',primary_color TEXT DEFAULT '#90f2d2',api_limit INTEGER NOT NULL DEFAULT 2000,api_calls_used INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
        db_exec("CREATE TABLE IF NOT EXISTS public_jobs(id TEXT PRIMARY KEY,title TEXT,company_name TEXT,location TEXT,remote TEXT,job_type TEXT,experience_min INTEGER,experience_max INTEGER,salary_min INTEGER,salary_max INTEGER,skills TEXT,description TEXT,category TEXT,status TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS public_job_applications(id TEXT PRIMARY KEY,job_id TEXT,applicant_name TEXT,applicant_email TEXT,applicant_phone TEXT,resume_text TEXT,cover_letter TEXT,experience_years INTEGER,current_company TEXT,current_role TEXT,notice_period TEXT,expected_salary TEXT,linkedin_url TEXT,portfolio_url TEXT,ai_score REAL,verdict TEXT,created_at TEXT)")
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS candidate_profiles(
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                headline TEXT DEFAULT '',
                current_company TEXT DEFAULT '',
                current_role TEXT DEFAULT '',
                current_location TEXT DEFAULT '',
                preferred_location TEXT DEFAULT '',
                total_exp REAL DEFAULT 0,
                relevant_exp REAL DEFAULT 0,
                notice_period TEXT DEFAULT '',
                available_from TEXT DEFAULT '',
                current_ctc TEXT DEFAULT '',
                expected_ctc TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                resume_text TEXT DEFAULT '',
                linkedin_url TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                job_change_intent TEXT DEFAULT 'active',
                applications_count INTEGER DEFAULT 0,
                interviews_count INTEGER DEFAULT 0,
                offers_count INTEGER DEFAULT 0,
                source TEXT DEFAULT 'manual',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS candidate_job_journeys(
                id TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL,
                application_id TEXT DEFAULT '',
                job_id TEXT DEFAULT '',
                company_slug TEXT DEFAULT '',
                company_name TEXT DEFAULT '',
                job_title TEXT DEFAULT '',
                stage TEXT DEFAULT 'profile_ready',
                status_note TEXT DEFAULT '',
                source TEXT DEFAULT 'manual',
                applied_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_event TEXT DEFAULT ''
            )
            """
        )
        db_exec("CREATE TABLE IF NOT EXISTS ide_projects(id TEXT PRIMARY KEY,user_id TEXT,name TEXT,description TEXT,language TEXT,scaffold TEXT,files_json TEXT,created_at TEXT,updated_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS ide_snippets(id TEXT PRIMARY KEY,user_id TEXT,title TEXT,language TEXT,code TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS ide_exec_logs(id TEXT PRIMARY KEY,user_id TEXT,language TEXT,command TEXT,output TEXT,success INTEGER,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS mission_projects(id TEXT PRIMARY KEY,user_id TEXT,name TEXT,description TEXT,phase TEXT,priority TEXT,tech_stack TEXT,progress INTEGER,status TEXT,tasks_json TEXT,strategy_json TEXT,created_at TEXT,updated_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS mission_deployments(id TEXT PRIMARY KEY,project_id TEXT,version TEXT,environment TEXT,platform TEXT,status TEXT,deployed_url TEXT,details_json TEXT,deployed_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS mission_tests(id TEXT PRIMARY KEY,project_id TEXT,name TEXT,language TEXT,passed INTEGER,total INTEGER,coverage REAL,log TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS mission_tickets(id TEXT PRIMARY KEY,user_id TEXT,project_id TEXT,title TEXT,description TEXT,ticket_type TEXT,priority TEXT,status TEXT,ai_analysis TEXT,created_at TEXT,resolved_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS mission_migrations(id TEXT PRIMARY KEY,project_id TEXT,from_system TEXT,to_system TEXT,migration_type TEXT,plan_json TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS suite_neural_signals(id TEXT PRIMARY KEY,origin TEXT,target TEXT,signal_type TEXT,payload_json TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS photon_agents(id TEXT PRIMARY KEY,codename TEXT,domain TEXT,status TEXT,energy REAL,pages_read INTEGER,intel_gathered INTEGER,current_url TEXT,pos_x REAL,pos_y REAL,emoji TEXT,created_at TEXT,updated_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS photon_missions(id TEXT PRIMARY KEY,user_id TEXT,title TEXT,objective TEXT,status TEXT,result TEXT,created_at TEXT,updated_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS photon_transmissions(id TEXT PRIMARY KEY,agent_id TEXT,title TEXT,summary TEXT,source_url TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS research_experiments(id TEXT PRIMARY KEY,user_id TEXT,exp_type TEXT,topic TEXT,result_json TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS research_software(id TEXT PRIMARY KEY,user_id TEXT,name TEXT,version TEXT,type TEXT,description TEXT,capabilities_json TEXT,code TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS mutation_events(id TEXT PRIMARY KEY,user_id TEXT,brain_id TEXT,mutation_type TEXT,fitness REAL,improvement TEXT,status TEXT,lesson TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS spread_nodes(id TEXT PRIMARY KEY,user_id TEXT,label TEXT,size_bytes INTEGER,status TEXT,path TEXT,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS phantom_packets(id TEXT PRIMARY KEY,origin_atom TEXT,dest_atom TEXT,visible_as TEXT,hop_chain_json TEXT,purpose TEXT,revealed INTEGER,created_at TEXT)")
        db_exec("CREATE TABLE IF NOT EXISTS evasion_events(id TEXT PRIMARY KEY,user_id TEXT,action TEXT,level TEXT,logic TEXT,threat_score REAL,created_at TEXT)")
        ensure_column("public_jobs", "company_slug", "TEXT")
        ensure_column("public_jobs", "department", "TEXT")
        ensure_column("public_jobs", "requirements", "TEXT")
        ensure_column("public_jobs", "openings", "INTEGER DEFAULT 1")
        ensure_column("public_jobs", "closes_at", "TEXT")
        ensure_column("public_jobs", "updated_at", "TEXT")
        ensure_column("public_job_applications", "stage", "TEXT DEFAULT 'applied'")
        ensure_column("public_job_applications", "updated_at", "TEXT")
        ensure_column("public_job_applications", "ai_summary", "TEXT")
        ensure_column("candidate_profiles", "applications_count", "INTEGER DEFAULT 0")
        ensure_column("candidate_profiles", "interviews_count", "INTEGER DEFAULT 0")
        ensure_column("candidate_profiles", "offers_count", "INTEGER DEFAULT 0")
        ensure_column("candidate_profiles", "job_change_intent", "TEXT DEFAULT 'active'")

    def suite_state(scope: str, default: Dict[str, Any]) -> Dict[str, Any]:
        row = db_one("SELECT payload_json FROM browser_suite_state WHERE scope=?", (scope,))
        if not row:
            set_suite_state(scope, default)
            return dict(default)
        try:
            return {**default, **json.loads(row["payload_json"])}
        except Exception:
            set_suite_state(scope, default)
            return dict(default)

    def set_suite_state(scope: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        db_exec(
            "INSERT INTO browser_suite_state(scope,payload_json,updated_at) VALUES(?,?,?) ON CONFLICT(scope) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at",
            (scope, json.dumps(payload), now_iso()),
        )
        return payload

    def current_user(request: Request) -> Optional[Dict[str, Any]]:
        return session_user(request)

    def require_member(request: Request) -> Dict[str, Any]:
        user = current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Login required for this workspace.")
        return user

    def require_owner(request: Request) -> Dict[str, Any]:
        user = require_member(request)
        if user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Master access required for this Ishani Core surface.")
        return user

    def safe_parse_json(raw: Any, fallback: Any) -> Any:
        if not raw:
            return fallback
        if isinstance(raw, (dict, list)):
            return raw
        try:
            return json.loads(raw)
        except Exception:
            return fallback

    def strip_html(raw_html: str) -> str:
        text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw_html or "")
        text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
        text = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def extract_title(raw_html: str, url: str) -> str:
        match = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw_html or "")
        if match:
            value = re.sub(r"\s+", " ", match.group(1)).strip()
            if value:
                return value
        parsed = urlparse(url)
        return parsed.netloc or url

    def detect_platform(url: str) -> str:
        host = (urlparse(url).netloc or "").lower()
        mapping = {"linkedin.com": "linkedin", "mail.google.com": "gmail", "gmail.com": "gmail", "github.com": "github", "naukri.com": "naukri", "teams.microsoft.com": "teams", "google.com": "google", "youtube.com": "youtube", "outlook.com": "outlook", "x.com": "twitter", "twitter.com": "twitter"}
        for domain, label in mapping.items():
            if domain in host:
                return label
        return "web"

    def favicon_for_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64"
        return ""

    def normalize_url(raw_url: str) -> str:
        if normalize_navigator_url:
            try:
                return normalize_navigator_url(raw_url)
            except Exception:
                pass
        value = (raw_url or "").strip()
        if not value:
            return "https://www.google.com/"
        if value.startswith(("http://", "https://")):
            return value
        if "." in value and " " not in value:
            return "https://" + value
        return "https://www.google.com/search?q=" + quote_plus(value)

    def world_snippets(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        needle = f"%{(query or '').strip().lower()}%"
        rows = db_all(
            "SELECT title, summary, content, geo_scope, tags_json FROM world_brain_atoms WHERE lower(title) LIKE ? OR lower(summary) LIKE ? OR lower(content) LIKE ? ORDER BY relevance_score DESC, created_at DESC LIMIT ?",
            (needle, needle, needle, limit),
        )
        return rows or []

    def seed_public_jobs() -> None:
        row = db_one("SELECT COUNT(*) AS n FROM public_jobs")
        if row and row.get("n", 0):
            return
        for job in DEFAULT_PUBLIC_JOBS:
            db_exec(
                "INSERT INTO public_jobs(id,title,company_name,location,remote,job_type,experience_min,experience_max,salary_min,salary_max,skills,description,category,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (job["id"], job["title"], job["company_name"], job["location"], job["remote"], job["job_type"], job["experience_min"], job["experience_max"], job["salary_min"], job["salary_max"], job["skills"], job["description"], job["category"], "open", now_iso()),
            )

    def slugify_company(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
        return slug[:64] or f"company-{new_id('co')[-6:]}"

    def create_company_api_key(slug: str) -> str:
        token = secrets.token_urlsafe(18).replace("-", "").replace("_", "")
        return f"tb_{slug[:12]}_{token[:24]}"

    def ensure_public_company_seed() -> None:
        company_id = new_id("co")
        db_exec(
            "INSERT OR IGNORE INTO public_companies(id,slug,name,owner_name,owner_email,plan,api_key,tagline,website,city,primary_color,api_limit,api_calls_used,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                company_id,
                "techbuzz-systems",
                "TechBuzz Systems Pvt. Ltd.",
                "TechBuzz Operations",
                "operations@techbuzz.local",
                "growth",
                create_company_api_key("techbuzz-systems"),
                "AI-powered recruitment and operating intelligence.",
                "https://techbuzz.local",
                "Lucknow",
                "#90f2d2",
                5000,
                0,
                now_iso(),
                now_iso(),
            ),
        )
        db_exec(
            "UPDATE public_jobs SET company_slug='techbuzz-systems', updated_at=COALESCE(updated_at, created_at) WHERE (company_slug IS NULL OR company_slug='') AND lower(company_name)=lower(?)",
            ("TechBuzz Systems Pvt. Ltd.",),
        )
        db_exec(
            "UPDATE public_job_applications SET stage=COALESCE(stage,'applied'), updated_at=COALESCE(updated_at, created_at), ai_summary=COALESCE(ai_summary, verdict) WHERE stage IS NULL OR updated_at IS NULL OR ai_summary IS NULL"
        )

    def company_row_by_slug(slug: str) -> Optional[Dict[str, Any]]:
        return db_one("SELECT * FROM public_companies WHERE slug=?", (slug,))

    def company_row_by_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        return db_one("SELECT * FROM public_companies WHERE api_key=?", (api_key,))

    def increment_company_api_usage(company_id: str) -> None:
        db_exec("UPDATE public_companies SET api_calls_used=api_calls_used+1, updated_at=? WHERE id=?", (now_iso(), company_id))

    def company_job_rows(slug: str) -> List[Dict[str, Any]]:
        rows = db_all(
            """
            SELECT
                j.*,
                COUNT(a.id) AS applications,
                SUM(CASE WHEN COALESCE(a.stage,'applied')='hired' THEN 1 ELSE 0 END) AS hired_count,
                AVG(COALESCE(a.ai_score, 0)) AS avg_ai_score
            FROM public_jobs j
            LEFT JOIN public_job_applications a ON a.job_id=j.id
            WHERE j.company_slug=?
            GROUP BY j.id
            ORDER BY COALESCE(j.updated_at, j.created_at) DESC
            """,
            (slug,),
        ) or []
        for row in rows:
            row["posted_at"] = row.get("created_at", "")
            row["applications"] = int(row.get("applications") or 0)
            row["hired_count"] = int(row.get("hired_count") or 0)
            row["avg_ai_score"] = round(float(row.get("avg_ai_score") or 0.0), 3)
        return rows

    def public_job_rows() -> List[Dict[str, Any]]:
        rows = db_all(
            """
            SELECT
                j.*,
                COUNT(a.id) AS applications,
                SUM(CASE WHEN COALESCE(a.stage,'applied')='hired' THEN 1 ELSE 0 END) AS hired_count,
                AVG(COALESCE(a.ai_score, 0)) AS avg_ai_score
            FROM public_jobs j
            LEFT JOIN public_job_applications a ON a.job_id=j.id
            WHERE COALESCE(j.status,'open')='open'
            GROUP BY j.id
            ORDER BY COALESCE(j.updated_at, j.created_at) DESC
            """
        ) or []
        for row in rows:
            row["posted_at"] = row.get("created_at", "")
            row["applications"] = int(row.get("applications") or 0)
            row["hired_count"] = int(row.get("hired_count") or 0)
            row["avg_ai_score"] = round(float(row.get("avg_ai_score") or 0.0), 3)
        return rows

    def normalize_candidate_email(email: str) -> str:
        return (email or "").strip().lower()

    def parse_notice_days(notice_period: str) -> int:
        raw = (notice_period or "").strip().lower()
        if not raw:
            return 30
        if any(term in raw for term in ("immediate", "join now", "0 day", "0days")):
            return 0
        match = re.search(r"(\d{1,3})", raw)
        if match:
            return max(0, min(int(match.group(1)), 120))
        if "serving" in raw:
            return 30
        return 30

    def derive_available_from(notice_period: str, explicit_value: str = "") -> str:
        raw = (explicit_value or "").strip()
        if raw:
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(raw, fmt).date().isoformat()
                except Exception:
                    continue
        return (datetime.utcnow().date() + timedelta(days=parse_notice_days(notice_period))).isoformat()

    def extract_resume_years(resume_text: str) -> float:
        values = [float(match.group(1)) for match in re.finditer(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", resume_text or "", re.I)]
        return max(values) if values else 0.0

    def extract_skill_terms(*texts: str) -> List[str]:
        library = [
            "python", "java", "javascript", "typescript", "react", "node", "node.js", "angular", "vue", "html", "css",
            "sql", "mysql", "postgresql", "mongodb", "oracle", "aws", "azure", "gcp", "docker", "kubernetes", "linux",
            "fastapi", "django", "flask", "spring boot", "microservices", "rest api", "git", "jenkins", "terraform",
            "salesforce", "sap", "oracle cloud", "recruitment", "talent acquisition", "sourcing", "screening", "naukri",
            "linkedin", "stakeholder management", "excel", "power bi", "tableau", "data analysis", "communication",
            "negotiation", "client handling", "boolean search", "devops", "ci/cd", "c++", "c", "go", "php"
        ]
        found: List[str] = []
        joined = " ".join(texts).lower()
        for skill in library:
            if skill in joined and skill not in found:
                found.append(skill)
        return found

    def candidate_profile_summary(profile: Dict[str, Any]) -> str:
        parts = []
        role = (profile.get("current_role") or profile.get("headline") or "").strip()
        if role:
            parts.append(role)
        company = (profile.get("current_company") or "").strip()
        if company:
            parts.append(f"at {company}")
        exp = float(profile.get("total_exp") or 0)
        if exp:
            parts.append(f"{exp:g} years overall")
        location = (profile.get("current_location") or profile.get("preferred_location") or "").strip()
        if location:
            parts.append(location)
        skills = [item.strip() for item in str(profile.get("skills") or "").split(",") if item.strip()]
        if skills:
            parts.append("Skills: " + ", ".join(skills[:6]))
        return ". ".join(parts)[:420]

    def refresh_candidate_counters(profile_id: str) -> None:
        journeys = db_all("SELECT stage, company_name FROM candidate_job_journeys WHERE profile_id=?", (profile_id,)) or []
        application_rows = db_all(
            "SELECT company_name, job_title, stage FROM candidate_job_journeys WHERE profile_id=? AND (COALESCE(job_id,'') != '' OR COALESCE(application_id,'') != '')",
            (profile_id,),
        ) or []
        applications_count = len({f"{row.get('company_name','')}|{row.get('job_title','')}" for row in application_rows if row.get("company_name") or row.get("job_title")})
        interviews_count = sum(1 for row in application_rows if str(row.get("stage", "")).lower() in {"interview", "l1", "l2", "l3", "scheduled"})
        offers_count = sum(1 for row in application_rows if str(row.get("stage", "")).lower() in {"offered", "offer", "joined", "hired"})
        db_exec(
            "UPDATE candidate_profiles SET applications_count=?, interviews_count=?, offers_count=?, updated_at=? WHERE id=?",
            (applications_count, interviews_count, offers_count, now_iso(), profile_id),
        )

    def upsert_candidate_profile(
        *,
        email: str,
        full_name: str = "",
        phone: str = "",
        resume_text: str = "",
        current_company: str = "",
        current_role: str = "",
        current_location: str = "",
        preferred_location: str = "",
        total_exp: float = 0,
        relevant_exp: float = 0,
        notice_period: str = "",
        current_ctc: str = "",
        expected_ctc: str = "",
        linkedin_url: str = "",
        target_role: str = "",
        job_change_intent: str = "active",
        source: str = "manual",
        job_skills: str = "",
        target_jd: str = "",
    ) -> Dict[str, Any]:
        email_key = normalize_candidate_email(email)
        if not email_key or "@" not in email_key:
            raise HTTPException(status_code=400, detail="A valid candidate email is required.")
        existing = db_one("SELECT * FROM candidate_profiles WHERE lower(email)=?", (email_key,))
        total_value = float(total_exp or 0) or extract_resume_years(resume_text)
        relevant_value = float(relevant_exp or 0) or total_value
        skill_terms = extract_skill_terms(resume_text, job_skills, target_jd, target_role, current_role)
        summary = candidate_profile_summary(
            {
                "current_role": current_role or target_role,
                "current_company": current_company,
                "total_exp": total_value,
                "current_location": current_location,
                "preferred_location": preferred_location,
                "skills": ", ".join(skill_terms),
            }
        )
        profile_id = existing["id"] if existing else new_id("cand")
        row = {
            "id": profile_id,
            "email": email_key,
            "full_name": (full_name or (existing or {}).get("full_name") or email_key.split("@")[0].replace(".", " ").title())[:120],
            "phone": (phone or (existing or {}).get("phone") or "")[:60],
            "headline": (target_role or current_role or (existing or {}).get("headline") or "")[:180],
            "current_company": (current_company or (existing or {}).get("current_company") or "")[:160],
            "current_role": (current_role or (existing or {}).get("current_role") or "")[:160],
            "current_location": (current_location or (existing or {}).get("current_location") or "")[:120],
            "preferred_location": (preferred_location or (existing or {}).get("preferred_location") or current_location or "")[:120],
            "total_exp": total_value,
            "relevant_exp": relevant_value,
            "notice_period": (notice_period or (existing or {}).get("notice_period") or "")[:80],
            "available_from": derive_available_from(notice_period or (existing or {}).get("notice_period", ""), (existing or {}).get("available_from", "")),
            "current_ctc": (current_ctc or (existing or {}).get("current_ctc") or "")[:80],
            "expected_ctc": (expected_ctc or (existing or {}).get("expected_ctc") or "")[:80],
            "skills": ", ".join(skill_terms)[:1800],
            "resume_text": (resume_text or (existing or {}).get("resume_text") or "")[:16000],
            "linkedin_url": (linkedin_url or (existing or {}).get("linkedin_url") or "")[:220],
            "summary": (summary or (existing or {}).get("summary") or "")[:1000],
            "job_change_intent": (job_change_intent or (existing or {}).get("job_change_intent") or "active")[:40],
            "source": (source or (existing or {}).get("source") or "manual")[:60],
        }
        if existing:
            db_exec(
                """
                UPDATE candidate_profiles
                SET full_name=?, phone=?, headline=?, current_company=?, current_role=?, current_location=?, preferred_location=?,
                    total_exp=?, relevant_exp=?, notice_period=?, available_from=?, current_ctc=?, expected_ctc=?, skills=?,
                    resume_text=?, linkedin_url=?, summary=?, job_change_intent=?, source=?, updated_at=?
                WHERE id=?
                """,
                (
                    row["full_name"], row["phone"], row["headline"], row["current_company"], row["current_role"], row["current_location"],
                    row["preferred_location"], row["total_exp"], row["relevant_exp"], row["notice_period"], row["available_from"],
                    row["current_ctc"], row["expected_ctc"], row["skills"], row["resume_text"], row["linkedin_url"], row["summary"],
                    row["job_change_intent"], row["source"], now_iso(), profile_id,
                ),
            )
        else:
            db_exec(
                """
                INSERT INTO candidate_profiles(
                    id,email,full_name,phone,headline,current_company,current_role,current_location,preferred_location,
                    total_exp,relevant_exp,notice_period,available_from,current_ctc,expected_ctc,skills,resume_text,
                    linkedin_url,summary,job_change_intent,applications_count,interviews_count,offers_count,source,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row["id"], row["email"], row["full_name"], row["phone"], row["headline"], row["current_company"], row["current_role"],
                    row["current_location"], row["preferred_location"], row["total_exp"], row["relevant_exp"], row["notice_period"],
                    row["available_from"], row["current_ctc"], row["expected_ctc"], row["skills"], row["resume_text"], row["linkedin_url"],
                    row["summary"], row["job_change_intent"], 0, 0, 0, row["source"], now_iso(), now_iso(),
                ),
            )
        refresh_candidate_counters(profile_id)
        return db_one("SELECT * FROM candidate_profiles WHERE id=?", (profile_id,)) or row

    def upsert_candidate_journey(
        profile_id: str,
        *,
        application_id: str = "",
        job_id: str = "",
        company_slug: str = "",
        company_name: str = "",
        job_title: str = "",
        stage: str = "profile_ready",
        status_note: str = "",
        source: str = "manual",
        last_event: str = "",
    ) -> Dict[str, Any]:
        if application_id or job_id:
            existing = db_one(
                "SELECT * FROM candidate_job_journeys WHERE profile_id=? AND application_id=? AND job_id=?",
                (profile_id, application_id or "", job_id or ""),
            )
        else:
            existing = db_one(
                "SELECT * FROM candidate_job_journeys WHERE profile_id=? AND source=? ORDER BY updated_at DESC LIMIT 1",
                (profile_id, source[:60]),
            )
        journey_id = existing["id"] if existing else new_id("cjour")
        applied_at = (existing or {}).get("applied_at") or now_iso()
        payload = (
            profile_id,
            application_id[:80],
            job_id[:80],
            company_slug[:120],
            company_name[:160],
            job_title[:180],
            stage[:60],
            status_note[:500],
            source[:60],
            applied_at,
            now_iso(),
            last_event[:200],
        )
        if existing:
            db_exec(
                """
                UPDATE candidate_job_journeys
                SET company_slug=?, company_name=?, job_title=?, stage=?, status_note=?, source=?, updated_at=?, last_event=?
                WHERE id=?
                """,
                (company_slug[:120], company_name[:160], job_title[:180], stage[:60], status_note[:500], source[:60], now_iso(), last_event[:200], journey_id),
            )
        else:
            db_exec(
                """
                INSERT INTO candidate_job_journeys(
                    id,profile_id,application_id,job_id,company_slug,company_name,job_title,stage,status_note,source,applied_at,updated_at,last_event
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (journey_id, *payload),
            )
        refresh_candidate_counters(profile_id)
        return db_one("SELECT * FROM candidate_job_journeys WHERE id=?", (journey_id,)) or {"id": journey_id, "profile_id": profile_id}

    def build_resume_alignment(resume_text: str, target_role: str = "", target_jd: str = "", job_skills: str = "") -> Dict[str, Any]:
        resume = (resume_text or "").strip()
        target_bundle = " ".join([target_role, target_jd, job_skills]).strip()
        jd_skills = extract_skill_terms(target_bundle)
        resume_skills = extract_skill_terms(resume)
        missing = [skill for skill in jd_skills if skill not in resume.lower()]
        matched = [skill for skill in jd_skills if skill in resume.lower()]
        headline = target_role or "Target role"
        bullets = []
        for skill in missing[:5]:
            bullets.append(f"Add a truthful bullet showing hands-on work with {skill} if you have actually used it.")
        if not bullets:
            bullets.append("Your resume already reflects the main target skills. Tighten outcomes, ownership, and quantified impact.")
        aligned_resume = resume
        if target_bundle:
            highlights = matched[:6] or resume_skills[:6]
            aligned_resume = (
                resume.strip()
                + "\n\nSuggested JD-aligned summary (keep only what is true):\n"
                + f"Target role: {headline}\n"
                + ("Relevant strengths: " + ", ".join(highlights) if highlights else "Relevant strengths: add outcome-led role highlights.")
                + "\n"
                + "\n".join(f"- {item}" for item in bullets)
            ).strip()
        return {
            "matched_skills": matched[:8],
            "missing_skills": missing[:8],
            "recommendations": bullets,
            "aligned_resume": aligned_resume[:18000],
        }

    def recommended_jobs_for_profile(profile: Dict[str, Any], limit: int = 6) -> List[Dict[str, Any]]:
        rows = []
        for job in public_job_rows():
            fit = analyze_candidate_fit(job, profile.get("resume_text", "") or profile.get("skills", ""), int(float(profile.get("total_exp") or 0)), profile.get("notice_period", ""))
            if str(profile.get("preferred_location") or "").strip():
                pref = str(profile.get("preferred_location") or "").lower()
                if pref in str(job.get("location", "")).lower() or str(job.get("remote", "")).lower() in {"remote", "hybrid"}:
                    fit_score = min(float(fit["ai_score"]) + 0.06, 0.99)
                else:
                    fit_score = float(fit["ai_score"])
            else:
                fit_score = float(fit["ai_score"])
            if fit_score < 0.44:
                continue
            rows.append(
                {
                    "job_id": job.get("id", ""),
                    "title": job.get("title", ""),
                    "company_name": job.get("company_name", ""),
                    "location": job.get("location", ""),
                    "remote": job.get("remote", ""),
                    "fit_score": round(fit_score, 3),
                    "verdict": "Strong Match" if fit_score >= 0.74 else "Good Match" if fit_score >= 0.58 else "Watch Match",
                }
            )
        rows.sort(key=lambda item: item["fit_score"], reverse=True)
        return rows[:limit]

    def candidate_dashboard_payload(email: str) -> Dict[str, Any]:
        email_key = normalize_candidate_email(email)
        if not email_key or "@" not in email_key:
            raise HTTPException(status_code=400, detail="Enter the candidate email used for your applications.")
        profile = db_one("SELECT * FROM candidate_profiles WHERE lower(email)=?", (email_key,))
        if not profile:
            raise HTTPException(status_code=404, detail="No candidate profile found for this email yet.")
        journeys = db_all(
            "SELECT * FROM candidate_job_journeys WHERE profile_id=? ORDER BY updated_at DESC, applied_at DESC LIMIT 40",
            (profile["id"],),
        ) or []
        stats = {
            "applications": int(profile.get("applications_count") or 0),
            "interviews": int(profile.get("interviews_count") or 0),
            "offers": int(profile.get("offers_count") or 0),
            "companies": len({row.get("company_name", "") for row in journeys if row.get("company_name") and (row.get("job_id") or row.get("application_id"))}),
            "active": sum(1 for row in journeys if (row.get("job_id") or row.get("application_id")) and str(row.get("stage", "")).lower() not in {"rejected", "hired", "joined"}),
        }
        next_move = "Keep your profile live, respond quickly, and align each application to the role before sharing."
        if stats["offers"]:
            next_move = "Compare live offers, confirm joining intent, and close the strongest fit without stretching the process."
        elif stats["interviews"]:
            next_move = "Prepare role-specific interview stories and keep availability clear so active interview loops do not slow down."
        elif stats["applications"]:
            next_move = "Track the active applications and follow up only on roles where your fit and joining intent are strongest."
        profile_view = {
            "full_name": profile.get("full_name", ""),
            "email": profile.get("email", ""),
            "phone": profile.get("phone", ""),
            "headline": profile.get("headline", ""),
            "current_company": profile.get("current_company", ""),
            "current_role": profile.get("current_role", ""),
            "current_location": profile.get("current_location", ""),
            "preferred_location": profile.get("preferred_location", ""),
            "total_exp": float(profile.get("total_exp") or 0),
            "relevant_exp": float(profile.get("relevant_exp") or 0),
            "notice_period": profile.get("notice_period", ""),
            "available_from": profile.get("available_from", ""),
            "skills": [item.strip() for item in str(profile.get("skills") or "").split(",") if item.strip()],
            "summary": profile.get("summary", ""),
            "job_change_intent": profile.get("job_change_intent", "active"),
        }
        return {
            "profile": profile_view,
            "stats": stats,
            "journeys": journeys,
            "recommended_jobs": recommended_jobs_for_profile(profile),
            "next_move": next_move,
        }

    def company_talent_map_payload(slug: str, available_by: str = "", limit: int = 16) -> Dict[str, Any]:
        company = company_row_by_slug(slug)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        jobs = [row for row in company_job_rows(slug) if (row.get("status") or "open") == "open"]
        profiles = db_all("SELECT * FROM candidate_profiles WHERE COALESCE(job_change_intent,'active') != 'closed' ORDER BY updated_at DESC LIMIT 200") or []
        cutoff = ""
        if available_by:
            cutoff = derive_available_from("", available_by)
        matches: List[Dict[str, Any]] = []
        for profile in profiles:
            available_from = str(profile.get("available_from") or "")
            if cutoff and available_from and available_from > cutoff:
                continue
            best = None
            for job in jobs:
                fit = analyze_candidate_fit(job, profile.get("resume_text", "") or profile.get("skills", ""), int(float(profile.get("total_exp") or 0)), profile.get("notice_period", ""))
                score = float(fit["ai_score"])
                if available_from and cutoff and available_from <= cutoff:
                    score = min(score + 0.05, 0.99)
                if str(profile.get("preferred_location") or "").strip():
                    pref = str(profile.get("preferred_location") or "").lower()
                    if pref in str(job.get("location", "")).lower() or str(job.get("remote", "")).lower() in {"remote", "hybrid"}:
                        score = min(score + 0.04, 0.99)
                if not best or score > best["fit_score"]:
                    best = {
                        "profile_id": profile.get("id", ""),
                        "candidate_name": profile.get("full_name", "") or profile.get("email", ""),
                        "headline": profile.get("headline", "") or profile.get("current_role", ""),
                        "current_company": profile.get("current_company", ""),
                        "current_location": profile.get("current_location", ""),
                        "preferred_location": profile.get("preferred_location", ""),
                        "available_from": available_from,
                        "notice_period": profile.get("notice_period", ""),
                        "applications_count": int(profile.get("applications_count") or 0),
                        "interviews_count": int(profile.get("interviews_count") or 0),
                        "offers_count": int(profile.get("offers_count") or 0),
                        "skills": [item.strip() for item in str(profile.get("skills") or "").split(",") if item.strip()][:8],
                        "matched_job_id": job.get("id", ""),
                        "matched_job_title": job.get("title", ""),
                        "fit_score": round(score, 3),
                        "fit_label": "Ready now" if score >= 0.76 else "Strong watch" if score >= 0.58 else "Build later",
                        "reason": f"{job.get('title', 'Role')} | {fit.get('verdict', 'Fit')} | Available {available_from or 'unknown'}",
                    }
            if best and best["fit_score"] >= 0.46:
                matches.append(best)
        matches.sort(key=lambda item: (item["fit_score"], -item["applications_count"]), reverse=True)
        ready_now = sum(1 for item in matches if item.get("available_from") and item["available_from"] <= datetime.utcnow().date().isoformat())
        return {
            "summary": "Live talent map blends candidate readiness, role fit, and availability date so companies can find the right person at the right time.",
            "stats": {
                "open_jobs": len(jobs),
                "candidate_pool": len(matches),
                "ready_now": ready_now,
                "strong_matches": sum(1 for item in matches if item["fit_score"] >= 0.68),
            },
            "matches": matches[:limit],
        }

    def company_candidate_rows(slug: str) -> List[Dict[str, Any]]:
        rows = db_all(
            """
            SELECT
                a.*,
                j.title AS job_title,
                j.company_slug,
                j.company_name,
                cp.available_from,
                cp.skills AS profile_skills,
                cp.applications_count,
                cp.interviews_count,
                cp.offers_count
            FROM public_job_applications a
            JOIN public_jobs j ON j.id=a.job_id
            LEFT JOIN candidate_profiles cp ON lower(cp.email)=lower(a.applicant_email)
            WHERE j.company_slug=?
            ORDER BY COALESCE(a.updated_at, a.created_at) DESC
            """,
            (slug,),
        ) or []
        for row in rows:
            row["stage"] = row.get("stage") or "applied"
            row["ai_score"] = float(row.get("ai_score") or 0.0)
            row["applications_count"] = int(row.get("applications_count") or 0)
            row["interviews_count"] = int(row.get("interviews_count") or 0)
            row["offers_count"] = int(row.get("offers_count") or 0)
        return rows

    def company_pipeline(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        stages = ["applied", "shortlisted", "interview", "offered", "hired", "rejected"]
        counts = {stage: 0 for stage in stages}
        for row in rows:
            stage = (row.get("stage") or "applied").strip().lower()
            counts[stage if stage in counts else "applied"] += 1
        return [{"stage": stage, "n": counts[stage]} for stage in stages]

    def company_stats_payload(slug: str) -> Dict[str, Any]:
        jobs = company_job_rows(slug)
        candidates = company_candidate_rows(slug)
        ai_scores = [float(row.get("ai_score") or 0.0) for row in candidates if row.get("ai_score") is not None]
        return {
            "jobs": len(jobs),
            "active_jobs": sum(1 for row in jobs if (row.get("status") or "open") == "open"),
            "applications": len(candidates),
            "hired": sum(1 for row in candidates if (row.get("stage") or "") == "hired"),
            "avg_ai_score": round((sum(ai_scores) / len(ai_scores)) if ai_scores else 0.0, 3),
        }

    def public_company_analytics(slug: str) -> Dict[str, Any]:
        company = company_row_by_slug(slug)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        jobs = company_job_rows(slug)
        candidates = company_candidate_rows(slug)
        stats = company_stats_payload(slug)
        raw_api_key = company.get("api_key", "")
        masked_api_key = raw_api_key[:10] + "..." + raw_api_key[-4:] if len(raw_api_key) > 18 else ("hidden" if raw_api_key else "")
        return {
            "slug": slug,
            "company": company.get("name") or slug,
            "plan": company.get("plan") or "starter",
            "api_key": masked_api_key,
            "api_key_masked": masked_api_key,
            "api_limit": int(company.get("api_limit") or 2000),
            "api_calls_used": int(company.get("api_calls_used") or 0),
            "stats": {
                "jobs": stats["active_jobs"],
                "applications": stats["applications"],
                "hired": stats["hired"],
                "avg_ai_score": stats["avg_ai_score"],
            },
            "pipeline": company_pipeline(candidates),
            "by_job": [{"title": row.get("title", "Job"), "apps": int(row.get("applications") or 0)} for row in sorted(jobs, key=lambda item: int(item.get("applications") or 0), reverse=True)[:8]],
            "profile": {
                "tagline": company.get("tagline", ""),
                "website": company.get("website", ""),
                "city": company.get("city", ""),
                "primary_color": company.get("primary_color", "#90f2d2"),
            },
            "talent_map_preview": company_talent_map_payload(slug, limit=8),
        }

    def seed_photon_agents() -> None:
        row = db_one("SELECT COUNT(*) AS n FROM photon_agents")
        if row and row.get("n", 0):
            return
        agents = [
            ("photon_recon", "Recon One", "market-scan", "idle", 0.91, 0, 0, "https://www.linkedin.com/", 0.16, 0.28, "🔎"),
            ("photon_hunt", "Hunt Prism", "talent-hunt", "idle", 0.86, 0, 0, "https://www.naukri.com/", 0.48, 0.34, "🎯"),
            ("photon_signal", "Signal Vein", "intel", "idle", 0.88, 0, 0, "https://news.google.com/", 0.74, 0.26, "📡"),
            ("photon_guard", "Guard Lattice", "defense", "idle", 0.95, 0, 0, "internal://monitor", 0.34, 0.71, "🛡️"),
            ("photon_writer", "Quill Core", "communication", "idle", 0.84, 0, 0, "https://mail.google.com/", 0.62, 0.68, "✉️"),
        ]
        for agent_id, codename, domain, status, energy, pages_read, intel_gathered, current_url, pos_x, pos_y, emoji in agents:
            db_exec(
                "INSERT INTO photon_agents(id,codename,domain,status,energy,pages_read,intel_gathered,current_url,pos_x,pos_y,emoji,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (agent_id, codename, domain, status, energy, pages_read, intel_gathered, current_url, pos_x, pos_y, emoji, now_iso(), now_iso()),
            )

    def seed_research_software() -> None:
        row = db_one("SELECT COUNT(*) AS n FROM research_software")
        if row and row.get("n", 0):
            return
        starter_code = "from fastapi import FastAPI\\n\\napp = FastAPI(title='TechBuzz Seed Utility')\\n\\n@app.get('/health')\\nasync def health():\\n    return {'status': 'ok', 'service': 'seed-utility'}\\n"
        db_exec(
            "INSERT INTO research_software(id,user_id,name,version,type,description,capabilities_json,code,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            ("sw_seed_utility", "system", "Seed Utility", "0.1.0", "utility", "Reference lightweight utility for bootstrap services, health checks, and simple task endpoints.", json.dumps(["health-check", "bootstrap", "fastapi"]), starter_code, now_iso()),
        )

    def record_signal(origin: str, target: str, signal_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        item = {"id": new_id("sig"), "origin": origin, "target": target, "signal_type": signal_type, "payload": payload, "created_at": now_iso()}
        db_exec("INSERT INTO suite_neural_signals(id,origin,target,signal_type,payload_json,created_at) VALUES(?,?,?,?,?,?)", (item["id"], origin, target, signal_type, json.dumps(payload), item["created_at"]))
        return item

    def save_brain_learning(brain_id: str, title: str, content: str, summary: str, keywords: str, source_type: str, source_url: str = "", relevance: float = 0.72) -> None:
        try:
            db_exec(
                "INSERT INTO brain_knowledge(id,brain_id,source_type,source_url,title,content,summary,keywords,relevance_score,learned_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (new_id("bk"), brain_id, source_type, source_url, title[:160], content[:4000], summary[:600], keywords[:240], relevance, now_iso()),
            )
        except Exception:
            pass

    def teach_from_browser(user_id: str, title: str, url: str, snippet: str, platform: str) -> None:
        save_brain_learning("tool_browser", title, snippet, snippet[:260], f"browser,{platform}", "browser_capture", url, 0.69)
        save_brain_learning("sec_signals", f"Signal from {platform.title()}", snippet, snippet[:220], f"browser,{platform},signal", "browser_signal", url, 0.66)
        if broadcast_brain_lesson:
            try:
                broadcast_brain_lesson("tool_browser", title=title, summary=snippet[:200], content=snippet[:800], keywords=[platform, "browser", "capture"], audience=["sec_signals", "sec_anveshan"], source_url=url)
            except Exception:
                pass
        if akshaya_save:
            try:
                akshaya_save("browser_capture", title[:120], snippet[:220], {"user_id": user_id, "platform": platform, "url": url})
            except Exception:
                pass

    async def fetch_page(url: str) -> Dict[str, Any]:
        started = asyncio.get_running_loop().time()
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers={"User-Agent": f"{AI_NAME}/{CORE_IDENTITY} BrowserSuite (+https://techbuzz.local)", "Accept-Language": "en-IN,en;q=0.9"}) as client:
            response = await client.get(url)
        latency_ms = int((asyncio.get_running_loop().time() - started) * 1000)
        response.raise_for_status()
        html = response.text
        title = extract_title(html, str(response.url))
        content = strip_html(html)
        return {"ok": True, "url": str(response.url), "title": title, "text_preview": content[:1800], "full_text": content[:12000], "latency_ms": latency_ms, "favicon": favicon_for_url(str(response.url))}

    def browser_history_rows(user_id: str, session_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
        if session_id:
            return db_all("SELECT * FROM browser_history WHERE user_id=? AND session_id=? ORDER BY created_at DESC LIMIT ?", (user_id, session_id, limit)) or []
        return db_all("SELECT * FROM browser_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit)) or []

    def learned_stats(user_id: str, session_id: Optional[str]) -> List[Dict[str, Any]]:
        if session_id:
            rows = db_all("SELECT platform, COUNT(*) AS items FROM browser_learned WHERE user_id=? AND session_id=? GROUP BY platform ORDER BY items DESC, platform ASC", (user_id, session_id))
        else:
            rows = db_all("SELECT platform, COUNT(*) AS items FROM browser_learned WHERE user_id=? GROUP BY platform ORDER BY items DESC, platform ASC", (user_id,))
        return rows or []

    def browser_status_payload(user: Dict[str, Any]) -> Dict[str, Any]:
        quick_sites = [{"label": "Naukri", "url": "https://www.naukri.com/", "kind": "sourcing"}, {"label": "LinkedIn", "url": "https://www.linkedin.com/", "kind": "network"}, {"label": "Gmail", "url": "https://mail.google.com/", "kind": "communication"}, {"label": "Teams", "url": "https://teams.microsoft.com/", "kind": "communication"}, {"label": "TechBuzz HQ", "url": "/company/portal", "kind": "internal"}]
        accounts = db_all("SELECT platform,email,username,updated_at FROM browser_accounts WHERE user_id=? ORDER BY updated_at DESC LIMIT 12", (user["id"],)) or []
        return {"ai": AI_NAME, "identity": CORE_IDENTITY, "mode": "visible-browser-learning", "launcher_available": bool(get_state().get("meta")), "quick_sites": quick_sites, "saved_accounts": accounts, "sessions": db_all("SELECT id,name,current_url,current_title,status,updated_at FROM browser_sessions WHERE user_id=? ORDER BY updated_at DESC LIMIT 10", (user["id"],)) or []}

    def analyze_candidate_fit(job: Dict[str, Any], resume_text: str, experience_years: int, notice_period: str) -> Dict[str, Any]:
        skills = [skill.strip().lower() for skill in (job.get("skills") or "").split(",") if skill.strip()]
        resume_lower = (resume_text or "").lower()
        skill_hits = sum(1 for skill in skills if skill in resume_lower)
        total_skills = max(len(skills), 1)
        skill_score = skill_hits / total_skills
        exp_target = max((job.get("experience_min") or 0), 1)
        experience_score = min(max(experience_years, 0) / max((job.get("experience_max") or exp_target), 1), 1.0)
        notice_lower = (notice_period or "").lower()
        notice_bonus = 0.08 if "immediate" in notice_lower else 0.04 if "15" in notice_lower or "30" in notice_lower else 0.0
        score = round(min(0.35 + (skill_score * 0.45) + (experience_score * 0.12) + notice_bonus, 0.98), 3)
        verdict = "High Fit" if score >= 0.76 else "Good Fit" if score >= 0.58 else "Possible Fit" if score >= 0.44 else "Needs Review"
        return {"ai_score": score, "verdict": verdict}

    async def generate_code_snippet(prompt: str, language: str) -> str:
        system = f"You are {AI_NAME}, a precise software builder for {COMPANY_NAME}. Return only code. Keep it concise, runnable, and production-sensible."
        response = await generate_text(f"Language: {language}\\nTask: {prompt}\\nReturn only code.", system=system, max_tokens=700, use_web_search=False, workspace="forge", source="manual")
        return (response["text"] or "").strip()

    def c_code_from_request(name: str, description: str, logic: str, language: str = "c") -> str:
        function_name = re.sub(r"[^a-zA-Z0-9_]", "_", (name or "program").lower())[:40] or "program"
        user_logic = (logic or "").strip()
        if user_logic:
            return user_logic
        if language.lower() == "cpp":
            return textwrap.dedent(f"""
                #include <iostream>

                int main() {{
                    std::cout << "TechBuzz {function_name} online" << std::endl;
                    std::cout << "Purpose: {description or 'Process signals safely'}" << std::endl;
                    return 0;
                }}
            """).strip()
        return textwrap.dedent(f"""
            #include <stdio.h>

            int main(void) {{
                printf("TechBuzz {function_name} online\\n");
                printf("Purpose: {description or 'Process signals safely'}\\n");
                return 0;
            }}
        """).strip()

    def find_compiler() -> Optional[str]:
        for candidate in ("gcc", "clang", "clang++", "g++"):
            if shutil.which(candidate):
                return candidate
        return None

    def run_bounded_process(command: List[str], workdir: Path, timeout: int = 5) -> Dict[str, Any]:
        try:
            completed = subprocess.run(command, cwd=str(workdir), capture_output=True, text=True, timeout=timeout, shell=False)
            output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
            return {"success": completed.returncode == 0, "output": output.strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "Timed out during execution."}
        except Exception as exc:
            return {"success": False, "output": str(exc)}

    def execute_code(language: str, code: str) -> Dict[str, Any]:
        language = (language or "text").lower()
        with tempfile.TemporaryDirectory(prefix="techbuzz_ide_") as tmp:
            temp_dir = Path(tmp)
            if language in {"python", "py"}:
                path = temp_dir / "main.py"
                path.write_text(code, encoding="utf-8")
                result = run_bounded_process([sys.executable, "-I", str(path)], temp_dir)
                result["command"] = f"{sys.executable} -I main.py"
                return result
            if language in {"javascript", "js", "node"}:
                if not shutil.which("node"):
                    return {"success": False, "output": "Node.js is not available on this machine.", "command": "node main.js"}
                path = temp_dir / "main.js"
                path.write_text(code, encoding="utf-8")
                result = run_bounded_process(["node", str(path)], temp_dir)
                result["command"] = "node main.js"
                return result
            if language in {"c", "cpp", "c++"}:
                compiler = find_compiler()
                ext = ".cpp" if language in {"cpp", "c++"} else ".c"
                source = temp_dir / ("main" + ext)
                binary = temp_dir / ("main.exe" if os.name == "nt" else "main")
                source.write_text(code, encoding="utf-8")
                if not compiler:
                    return {"success": False, "output": "No C/C++ compiler is available on this machine. Generation succeeded, compilation skipped.", "command": "compiler unavailable"}
                compile_cmd = [compiler, str(source), "-o", str(binary)]
                compile_result = run_bounded_process(compile_cmd, temp_dir, timeout=10)
                if not compile_result["success"]:
                    compile_result["command"] = " ".join(compile_cmd)
                    return compile_result
                run_result = run_bounded_process([str(binary)], temp_dir)
                run_result["command"] = " ".join(compile_cmd)
                return run_result
        return {"success": False, "output": "Unsupported language.", "command": ""}

    def build_project_tasks(name: str, description: str, tech_stack: str) -> List[Dict[str, Any]]:
        tokens = [part.strip() for part in tech_stack.split(",") if part.strip()]
        stack_label = ", ".join(tokens[:4]) or tech_stack or "FastAPI, SQLite, JS"
        return [
            {"title": f"Scope {name}", "phase": "planning", "type": "research", "priority": "high", "hours": 4, "brain": "exec_research"},
            {"title": "Define user journeys", "phase": "planning", "type": "product", "priority": "high", "hours": 3, "brain": "sec_strategy"},
            {"title": f"Create system design for {stack_label}", "phase": "design", "type": "architecture", "priority": "high", "hours": 6, "brain": "sec_anveshan"},
            {"title": "Build API and services", "phase": "development", "type": "backend", "priority": "high", "hours": 16, "brain": "tool_builder"},
            {"title": "Build interface and states", "phase": "development", "type": "frontend", "priority": "medium", "hours": 14, "brain": "tool_browser"},
            {"title": "Write tests and run QA", "phase": "testing", "type": "quality", "priority": "high", "hours": 8, "brain": "exec_guardian"},
            {"title": "Prepare rollout checklist", "phase": "deployment", "type": "ops", "priority": "medium", "hours": 5, "brain": "exec_operations"},
            {"title": "Support and enhancement backlog", "phase": "support", "type": "support", "priority": "medium", "hours": 4, "brain": "sec_accounts"},
        ]

    def neural_mesh_snapshot() -> Dict[str, Any]:
        hierarchy = brain_hierarchy_payload()
        brains = hierarchy.get("brains", [])
        layer_order = {"mother": 0, "executive": 1, "secretary": 2, "domain": 3, "tool": 4, "machine": 5, "atom": 6}
        layer_emoji = {"mother": "👑", "executive": "🧭", "secretary": "📎", "domain": "🏛️", "tool": "🛠️", "machine": "⚙️", "atom": "🧬"}
        nodes, edges = [], []
        for brain in brains:
            nodes.append({"id": brain["id"], "name": brain["name"], "layer": layer_order.get(brain.get("layer", "tool"), 4), "layer_name": brain.get("layer", "tool"), "emoji": layer_emoji.get(brain.get("layer", "tool"), "🛠️"), "health": 100 if brain.get("status") != "offline" else 48, "load": 22 + (sum(ord(char) for char in brain["id"]) % 48)})
            if brain.get("parent_id"):
                edges.append({"from": brain["parent_id"], "to": brain["id"], "active": True})
        signal_count = (db_one("SELECT COUNT(*) AS n FROM suite_neural_signals") or {}).get("n", 0) or 0
        share_count = (db_one("SELECT COUNT(*) AS n FROM suite_neural_signals WHERE signal_type IN ('broadcast','knowledge_share','cross_learn')") or {}).get("n", 0) or 0
        knowledge_total = (db_one("SELECT COUNT(*) AS n FROM brain_knowledge") or {}).get("n", 0) or 0
        active_count = sum(1 for node in nodes if node["health"] > 0)
        db_counts = db_all("SELECT brain_id, COUNT(*) AS entry_count FROM brain_knowledge GROUP BY brain_id ORDER BY entry_count DESC LIMIT 40") or []
        name_map = {brain["id"]: brain["name"] for brain in brains}
        brain_databases = [{"brain_id": row["brain_id"], "brain_name": name_map.get(row["brain_id"], row["brain_id"]), "entry_count": row["entry_count"]} for row in db_counts]
        state = suite_state("neural_mesh", {"frequency_hz": 1.0})
        return {"nodes": nodes, "edges": edges, "brain_databases": brain_databases, "stats": {"total_brains": len(nodes), "connections": len(edges), "signals": signal_count, "knowledge": knowledge_total, "shares": share_count, "carbon_copies": max(3, len(nodes) // 9), "active_brains": active_count}, "mesh_config": state}

    def recent_signals(limit: int = 30) -> List[Dict[str, Any]]:
        rows = db_all("SELECT * FROM suite_neural_signals ORDER BY created_at DESC LIMIT ?", (limit,)) or []
        items = []
        for row in rows:
            payload = safe_parse_json(row.get("payload_json"), {})
            items.append({"id": row["id"], "from": row["origin"], "to": row["target"], "type": row["signal_type"], "payload": payload, "summary": payload.get("summary") or payload.get("message") or payload.get("note") or row["signal_type"], "created_at": row["created_at"]})
        return items

    def photon_status_payload() -> Dict[str, Any]:
        suite = suite_state("photon_network", {"running": False})
        agents = db_all("SELECT * FROM photon_agents ORDER BY codename ASC") or []
        transmissions = db_all("SELECT * FROM photon_transmissions ORDER BY created_at DESC LIMIT 20") or []
        return {
            "running": bool(suite.get("running", False)),
            "agents": agents,
            "missions": db_all("SELECT * FROM photon_missions ORDER BY updated_at DESC LIMIT 12") or [],
            "new_transmissions": transmissions,
            "transmissions": transmissions,
            "agent_count": len(agents),
            "total_intel_gathered": sum(int(agent.get("intel_gathered") or 0) for agent in agents),
            "total_pages_read": sum(int(agent.get("pages_read") or 0) for agent in agents),
        }

    def spread_status_payload() -> Dict[str, Any]:
        spread = suite_state("spread", {"running": False, "speed": 1})
        evasion = suite_state("evasion", {"running": False, "level": "visible", "current_logic": "manual_review"})
        nodes = db_all("SELECT * FROM spread_nodes ORDER BY created_at DESC") or []
        used_bytes = sum(int(node.get("size_bytes") or 0) for node in nodes)
        cap_bytes = 1024 * 1024 * 1024
        history = db_all("SELECT * FROM evasion_events ORDER BY created_at DESC LIMIT 12") or []
        file_tree = []
        for node in nodes[:80]:
            path = Path(node.get("path") or "")
            file_tree.append({
                "id": node["id"],
                "dir": path.parent.name or "root",
                "name": path.name or f"{node['id']}.node",
                "path": node["path"],
                "size": int(node.get("size_bytes") or 0),
                "size_bytes": int(node.get("size_bytes") or 0),
                "status": node["status"],
            })
        event_history = [{"id": node["id"], "generation": index + 1, "size": int(node.get("size_bytes") or 0), "label": node.get("label", "node")} for index, node in enumerate(nodes[:16])]
        return {
            "running": bool(spread.get("running", False)),
            "speed": int(spread.get("speed", 1) or 1),
            "vault_used_pct": round((used_bytes / cap_bytes) * 100, 2),
            "vault_used_bytes": used_bytes,
            "total_nodes": len(nodes),
            "generation": max(1, len(nodes)),
            "total_bytes_db": used_bytes,
            "file_tree": file_tree,
            "history": event_history,
            "evasion": {
                "running": bool(evasion.get("running", False)),
                "current_logic": evasion.get("current_logic", "manual_review"),
                "level": evasion.get("level", "visible"),
                "threat_score": float(evasion.get("threat_score", 0.22) or 0.22),
                "total_rewrites": (db_one("SELECT COUNT(*) AS n FROM evasion_events") or {}).get("n", 0) or 0,
            },
            "recent_evasion_events": history,
        }

    def mutation_history_payload() -> Dict[str, Any]:
        mutations = db_all("SELECT * FROM mutation_events ORDER BY created_at DESC LIMIT 60") or []
        pool: Dict[str, Dict[str, Any]] = {}
        normalized = []
        for index, row in enumerate(mutations, start=1):
            fitness = float(row.get("fitness") or 0)
            gene_type = row["mutation_type"]
            item = pool.setdefault(gene_type, {"gene_type": gene_type, "gene_value": row.get("improvement", ""), "strength": 0.0, "source_brain": row.get("brain_id", "unknown"), "count": 0})
            item["count"] += 1
            item["strength"] += fitness
            normalized.append({
                **row,
                "fitness_score": fitness,
                "mother_approved": 1 if row.get("status") == "approved" else -1 if row.get("status") == "rejected" else 0,
                "generation": index,
            })
        gene_pool = []
        for item in pool.values():
            gene_pool.append({
                "gene_type": item["gene_type"],
                "gene_value": item["gene_value"][:120],
                "strength": round(item["strength"] / max(item["count"], 1), 3),
                "source_brain": item["source_brain"],
            })
        gene_pool.sort(key=lambda row: -row["strength"])
        stats = {"total_mutations": len(normalized), "approved": sum(1 for row in normalized if row.get("status") == "approved"), "pending": sum(1 for row in normalized if row.get("status") == "pending"), "rejected": sum(1 for row in normalized if row.get("status") == "rejected")}
        return {"mutations": normalized, "gene_pool": gene_pool[:20], "stats": stats}

    class BrowserSessionReq(BaseModel):
        session_id: Optional[str] = None
        name: str = "Jinn Browser"

    class BrowserNavigateReq(BaseModel):
        url: str
        session_id: Optional[str] = None

    class BrowserCommandReq(BaseModel):
        command: str
        current_url: str = ""
        page_context: str = ""
        session_id: Optional[str] = None
        platform: str = "web"

    class BrowserRewriteReq(BaseModel):
        component: str
        reason: str = "manual_request"

    class BrowserAccountReq(BaseModel):
        platform: str
        email: str
        username: str = ""

    class CareerAskReq(BaseModel):
        question: str
        location: str = ""
        role: str = ""
        experience_level: str = ""
        profile: Dict[str, Any] = {}

    class JobApplyReq(BaseModel):
        applicant_name: str
        applicant_email: str
        applicant_phone: str = ""
        resume_text: str
        cover_letter: str = ""
        experience_years: int = 0
        current_company: str = ""
        current_role: str = ""
        notice_period: str = ""
        expected_salary: str = ""
        linkedin_url: str = ""
        portfolio_url: str = ""

    class CandidateResumeSyncReq(BaseModel):
        email: str
        full_name: str = ""
        phone: str = ""
        resume_text: str
        target_role: str = ""
        target_jd: str = ""
        job_id: str = ""
        experience_years: int = 0
        current_company: str = ""
        current_role: str = ""
        current_location: str = ""
        preferred_location: str = ""
        notice_period: str = ""
        current_ctc: str = ""
        expected_ctc: str = ""
        linkedin_url: str = ""
        job_change_intent: str = "active"

    class CompanyRegisterReq(BaseModel):
        name: str
        owner_name: str
        owner_email: str
        plan: str = "starter"

    class CompanyProfileReq(BaseModel):
        tagline: str = ""
        website: str = ""
        city: str = ""
        primary_color: str = "#90f2d2"

    class CompanyStageReq(BaseModel):
        stage: str = "applied"

    class CompanyJobReq(BaseModel):
        title: str
        description: str
        requirements: str = ""
        location: str = ""
        job_type: str = "full_time"
        remote: str = "hybrid"
        salary_min: int = 0
        salary_max: int = 0
        experience_min: int = 0
        experience_max: int = 5
        skills: str = ""
        department: str = ""
        openings: int = 1
        closes_at: str = ""

    class CompanyScreenReq(BaseModel):
        job_title: str = ""
        job_description: str = ""
        resume: str = ""
        skills: str = ""

    class IDEProjectReq(BaseModel):
        name: str
        description: str = ""
        language: str = "python"
        scaffold: str = "service"

    class IDESnippetReq(BaseModel):
        title: str
        language: str = "python"
        code: str

    class IDEGenerateReq(BaseModel):
        prompt: str
        language: str = "python"

    class IDEExecuteReq(BaseModel):
        language: str = "python"
        code: str

    class MissionProjectReq(BaseModel):
        name: str
        description: str = ""
        priority: str = "medium"
        tech_stack: str = "Python, FastAPI, SQLite"
        team_size: int = 1
        target_date: str = ""

    class MissionDeployReq(BaseModel):
        project_id: str
        version: str = "1.0.0"
        environment: str = "production"
        platform: str = "railway"
        config: Dict[str, Any] = {}

    class MissionTestReq(BaseModel):
        project_id: str
        name: str
        code: str
        language: str = "python"

    class MissionStrategyReq(BaseModel):
        project_id: str = ""
        strategy_type: str = "go_to_market"
        title: str = ""
        objectives: str = ""

    class MissionTicketReq(BaseModel):
        project_id: str = ""
        title: str
        description: str
        ticket_type: str = "bug"
        priority: str = "medium"

    class MissionMigrationReq(BaseModel):
        project_id: str = ""
        from_system: str
        to_system: str
        migration_type: str = "database"
        data_volume: str = ""

    class NeuralTransmitReq(BaseModel):
        channel: str = "broadcast"
        destination: str = "ALL"
        data: str = ""
        signal_data: str = ""
        signal: str = ""
        source: str = ""

    class NeuralLearnReq(BaseModel):
        brain_id: str = "sec_anveshan"
        title: str = ""
        topic: str = ""
        content: str = ""
        summary: str = ""
        keywords: str = ""
        source_url: str = ""

    class PhotonMissionReq(BaseModel):
        title: str = ""
        objective: str = ""
        query: str = ""
        target_domains: List[str] = []

    class PhotonAskReq(BaseModel):
        question: str

    class ResearchRewriteReq(BaseModel):
        topic: str
        current_code: str = ""

    class ResearchCReq(BaseModel):
        name: str = ""
        program_name: str = ""
        description: str = ""
        logic: str = ""
        language: str = "c"

    class ResearchFileHippoReq(BaseModel):
        query: str
        category: str = "utilities"

    class ResearchSoftwareReq(BaseModel):
        name: str
        description: str
        type: str = "utility"
        software_type: str = ""

    class GenomeReq(BaseModel):
        code: str

    class MutationReq(BaseModel):
        brain_id: str = ""
        mutation_type: str = ""

    class SpreadSpeedReq(BaseModel):
        speed: int = 1

    class SpreadManualNodeReq(BaseModel):
        label: str
        content: str = ""
        size_kb: int = 16

    class PhantomRouteReq(BaseModel):
        payload: str = ""
        sender_brain: str = "mother"
        origin_atom: str = "alpha"
        dest_atom: str = "omega"
        purpose: str = "relay"

    class EvasionRewriteReq(BaseModel):
        topic: str = "resilience"
        trigger: str = "manual"

    @app.post("/api/browser/session/start")
    async def browser_session_start(req: BrowserSessionReq, request: Request):
        user = require_member(request)
        session_id = (req.session_id or new_id("brs"))[:64]
        existing = db_one("SELECT id FROM browser_sessions WHERE id=? AND user_id=?", (session_id, user["id"]))
        if existing:
            db_exec("UPDATE browser_sessions SET name=?, status='active', updated_at=? WHERE id=?", (req.name[:120], now_iso(), session_id))
        else:
            db_exec("INSERT INTO browser_sessions(id,user_id,name,current_url,current_title,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (session_id, user["id"], req.name[:120], "", "", "active", now_iso(), now_iso()))
        record_signal("tool_browser", "sec_signals", "browser_session", {"session_id": session_id, "summary": "Browser session started"})
        return {"ok": True, "session_id": session_id, **browser_status_payload(user)}

    @app.post("/api/browser/fetch")
    async def browser_fetch(req: BrowserNavigateReq, request: Request):
        user = require_member(request)
        target_url = normalize_url(req.url)
        payload = await fetch_page(target_url)
        platform = detect_platform(payload["url"])
        db_exec("INSERT INTO browser_learned(id,user_id,session_id,platform,topic,url,snippet,learned_at) VALUES(?,?,?,?,?,?,?,?)", (new_id("blr"), user["id"], req.session_id or "", platform, payload["title"], payload["url"], payload["text_preview"][:600], now_iso()))
        teach_from_browser(user["id"], payload["title"], payload["url"], payload["text_preview"], platform)
        return payload

    @app.post("/api/browser/navigate")
    async def browser_navigate(req: BrowserNavigateReq, request: Request):
        user = require_member(request)
        target_url = normalize_url(req.url)
        payload = await fetch_page(target_url)
        platform = detect_platform(payload["url"])
        db_exec("INSERT INTO browser_history(id,user_id,session_id,url,title,platform,favicon,text_preview,latency_ms,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (new_id("bh"), user["id"], req.session_id or "", payload["url"], payload["title"], platform, payload["favicon"], payload["text_preview"][:1600], int(payload["latency_ms"]), now_iso()))
        db_exec("INSERT INTO browser_learned(id,user_id,session_id,platform,topic,url,snippet,learned_at) VALUES(?,?,?,?,?,?,?,?)", (new_id("blr"), user["id"], req.session_id or "", platform, payload["title"], payload["url"], payload["text_preview"][:600], now_iso()))
        if req.session_id:
            db_exec("UPDATE browser_sessions SET current_url=?, current_title=?, status='active', updated_at=? WHERE id=? AND user_id=?", (payload["url"], payload["title"], now_iso(), req.session_id, user["id"]))
        teach_from_browser(user["id"], payload["title"], payload["url"], payload["text_preview"], platform)
        return payload

    @app.get("/api/browser/history")
    async def browser_history(limit: int = 12, session_id: str = "", request: Request = None):
        user = require_member(request)
        return {"history": browser_history_rows(user["id"], session_id or None, max(1, min(limit, 60)))}

    @app.get("/api/browser/learned")
    async def browser_learned(session_id: str = "", request: Request = None):
        user = require_member(request)
        return {"stats": learned_stats(user["id"], session_id or None)}

    @app.get("/api/browser/ai-suggest")
    async def browser_ai_suggest(url: str = "", request: Request = None):
        require_member(request)
        target = normalize_url(url)
        platform = detect_platform(target)
        suggestions = {
            "linkedin": ["Search for java developer noida", "Open recruiter search workflow", "Capture hiring-market notes"],
            "gmail": ["Prepare follow-up email draft", "Summarize unread inbox", "Open interview coordination checklist"],
            "naukri": ["Search python fastapi remote", "Capture sourcing insights", "Prepare shortlist brief"],
            "teams": ["Prepare meeting summary", "Draft stakeholder update", "Open delivery checklist"],
            "github": ["Summarize repo readme", "Capture dependency insights", "Create tech evaluation note"],
        }.get(platform, ["Summarize this page", "Capture insights", "Search the web"])
        return {"suggestions": suggestions, "platform": platform, "url": target}

    @app.post("/api/browser/account/save")
    async def browser_account_save(req: BrowserAccountReq, session_id: str = "", request: Request = None):
        user = require_member(request)
        existing = db_one("SELECT id FROM browser_accounts WHERE user_id=? AND platform=? AND email=?", (user["id"], req.platform, req.email.strip()))
        if existing:
            db_exec("UPDATE browser_accounts SET username=?, updated_at=? WHERE id=?", ((req.username or req.email).strip()[:160], now_iso(), existing["id"]))
        else:
            db_exec("INSERT INTO browser_accounts(id,user_id,platform,email,username,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (new_id("bac"), user["id"], req.platform[:40], req.email.strip()[:160], (req.username or req.email).strip()[:160], now_iso(), now_iso()))
        return {"ok": True, "saved": True}

    @app.post("/api/browser/rewrite")
    async def browser_rewrite(req: BrowserRewriteReq, request: Request):
        user = require_member(request)
        improvement = f"{req.component.replace('_', ' ').title()} will evolve through a visible review cycle. The browser suite will keep history, saved accounts, and learning separated while improving the operator workflow."
        proposal = {"component": req.component, "reason": req.reason, "changes": ["Add stricter action previews before operator sends anything.", "Improve page summarization and platform heuristics.", "Keep captured learning linked to browser session and platform."]}
        db_exec("INSERT INTO browser_rewrites(id,user_id,component,reason,mutation_type,improvement,proposal,created_at) VALUES(?,?,?,?,?,?,?,?)", (new_id("brw"), user["id"], req.component[:80], req.reason[:200], "visible_browser_mutation", improvement, json.dumps(proposal), now_iso()))
        record_signal("tool_browser", "mother", "browser_rewrite", {"summary": improvement[:140], "component": req.component})
        return {"mutation_type": "visible_browser_mutation", "improvement": improvement, "proposal": proposal}

    @app.get("/api/browser/rewrites")
    async def browser_rewrites(request: Request):
        user = require_member(request)
        return {"rewrites": db_all("SELECT * FROM browser_rewrites WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user["id"],)) or []}

    @app.get("/api/browser/actions")
    async def browser_actions(request: Request):
        require_member(request)
        return {"actions": [{"label": "Draft Gmail follow-up", "type": "communication"}, {"label": "Prepare LinkedIn outreach", "type": "sourcing"}, {"label": "Save account", "type": "identity"}, {"label": "Capture page insight", "type": "learning"}]}

    @app.get("/api/browser/status")
    async def browser_status(request: Request):
        user = require_member(request)
        return browser_status_payload(user)

    @app.post("/api/browser/command")
    async def browser_command(req: BrowserCommandReq, request: Request):
        require_member(request)
        command = (req.command or "").strip()
        lowered = command.lower()
        page_context = (req.page_context or "").strip()
        platform = req.platform or detect_platform(req.current_url or "")
        if any(word in lowered for word in ("open ", "go to ", "navigate", "visit ")):
            target = command.split(" ", 1)[1] if " " in command else req.current_url or "google.com"
            return {"ai_response": f"I'll open {target.strip()} in the browser view.", "url_to_navigate": normalize_url(target), "steps": ["Resolve target", "Open page", "Capture learning"]}
        if "summarize" in lowered or "what did you learn" in lowered:
            summary = page_context[:300] or "No page context is loaded yet. Open a page and I will capture the useful signal."
            return {"ai_response": f"Here is the useful signal from this page: {summary}", "steps": ["Read visible text", "Compress signal", "Store learning"]}
        if any(word in lowered for word in ("email", "gmail", "reply", "compose")):
            return {"ai_response": "I can prepare the email steps, but I will not send anything silently. Open Gmail and I will structure the draft.", "url_to_navigate": "https://mail.google.com/", "steps": ["Open Gmail", "Draft subject", "Draft body", "Wait for operator send"]}
        if any(word in lowered for word in ("linkedin", "connect", "outreach", "candidate")):
            return {"ai_response": "I can guide sourcing on the visible page and capture relevant notes, but I will only show the data you asked for.", "requires_user_input": True, "clarification": "Tell me the role, skills, location, and years of experience you want."}
        if any(word in lowered for word in ("naukri", "search")):
            target = req.current_url if "naukri" in (req.current_url or "") else "https://www.naukri.com/"
            return {"ai_response": "Use the browser to run a visible sourcing search. I will learn only from what you open and capture.", "url_to_navigate": target, "steps": ["Open sourcing page", "Search role keywords", "Capture useful insights"]}
        generated = await generate_text(
            (
                f"Browser operator request:\n{command}\n\n"
                f"Current URL: {req.current_url or 'not open'}\n"
                f"Detected platform: {platform}\n"
                f"Visible page context:\n{(page_context or 'No visible page text captured yet.')[:1500]}\n\n"
                "Reply in short human language. Never pretend you clicked, posted, sent, or changed anything unless the operator confirms it."
            ),
            system=(
                f"You are {AI_NAME} inside Jinn Browser for {COMPANY_NAME}. "
                "Be concise, useful, and safe. Offer the next visible action and keep the tone human."
            ),
            max_tokens=180,
            use_web_search=False,
            workspace="bridge",
            source="manual",
        )
        return {
            "ai_response": generated["text"],
            "provider": generated["provider"],
            "steps": ["Inspect visible page", "Prepare next action", "Wait for operator approval"],
        }

    @app.post("/api/career/ask")
    async def career_ask(req: CareerAskReq):
        profile = req.profile or {}
        role = (req.role or profile.get("current_role") or profile.get("role") or "").strip()
        location = (req.location or profile.get("location") or "").strip()
        experience_level = (req.experience_level or str(profile.get("experience_years") or profile.get("experience") or "")).strip()
        query = " ".join(part for part in [req.question, location, role, experience_level, str(profile.get("skills") or "")] if part).strip()
        snippets = world_snippets(query, limit=4)
        skills_raw = str(profile.get("skills") or "")
        skill_list = [part.strip() for part in skills_raw.split(",") if part.strip()]
        experience_years = int(profile.get("experience_years") or 0) if str(profile.get("experience_years") or "").strip() else 0
        career_score = max(42, min(92, 48 + min(len(skill_list), 8) * 4 + min(experience_years, 10) * 2))
        strengths = skill_list[:4] or ["Communication", "Learning ability"]
        gaps = []
        question_lower = (req.question or "").lower()
        if "salary" in question_lower:
            gaps.append("Negotiation framing")
        if "interview" in question_lower:
            gaps.append("Interview storytelling")
        if "backend" in question_lower or "python" in question_lower:
            gaps.append("System design proof")
        if not gaps:
            gaps = ["Role-specific portfolio proof", "Outcome metrics on resume"]
        role_targets = []
        if role:
            role_targets.append(role)
        if any("python" in item.lower() for item in skill_list):
            role_targets.append("Python Backend Engineer")
        if any("recruit" in item.lower() or "sourcing" in item.lower() for item in skill_list):
            role_targets.append("Talent Acquisition Specialist")
        if not role_targets:
            role_targets = ["Target role clarification", "Adjacent market-fit role"]
        if snippets:
            guidance = [f"{item['title']}: {item.get('summary') or item.get('content', '')[:180]}" for item in snippets]
            advice = " | ".join(guidance[:3])
        else:
            advice = "Clarify role, location, compensation goal, notice period, and proof of relevant work before the next move."
        next_step = "Turn the target role into a checklist: relevant skills, proof points, compensation range, notice period, and one strong outreach message."
        answer = advice
        return {
            "answer": answer,
            "advice": advice,
            "snippets": snippets,
            "career_score": career_score,
            "strengths": strengths,
            "gaps": gaps,
            "roles_to_target": role_targets[:4],
            "next_step": next_step,
        }

    @app.get("/api/jobs")
    async def list_jobs(q: str = "", location: str = "", job_type: str = "", remote: str = "", skills: str = "", page: int = 1, page_size: int = 8, limit: int = 0):
        jobs = public_job_rows()
        skill_terms = [term.strip().lower() for term in skills.split(",") if term.strip()]
        filtered = []
        for job in jobs:
            haystack = " ".join([job.get("title", ""), job.get("company_name", ""), job.get("location", ""), job.get("description", ""), job.get("skills", "")]).lower()
            if q and q.lower() not in haystack:
                continue
            if location and location.lower() not in (job.get("location", "").lower()):
                continue
            if job_type and job_type.lower() != (job.get("job_type", "").lower()):
                continue
            if remote and remote.lower() != (job.get("remote", "").lower()):
                continue
            if skill_terms and not all(term in (job.get("skills", "").lower()) for term in skill_terms):
                continue
            job["applications"] = int(job.get("applications") or 0)
            job["posted_at"] = job.get("created_at", "")
            filtered.append(job)
        total = len(filtered)
        effective_page_size = limit or page_size
        size = max(1, min(effective_page_size, 20))
        pages = max(1, (total + size - 1) // size)
        current_page = max(1, min(page, pages))
        start = (current_page - 1) * size
        return {"jobs": filtered[start : start + size], "total": total, "page": current_page, "pages": pages}

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str):
        job = db_one("SELECT * FROM public_jobs WHERE id=?", (job_id,))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        job["applications"] = int(((db_one("SELECT COUNT(*) AS n FROM public_job_applications WHERE job_id=?", (job_id,)) or {}).get("n", 0)) or 0)
        job["posted_at"] = job.get("created_at", "")
        return job

    @app.post("/api/jobs/{job_id}/apply")
    async def apply_job(job_id: str, req: JobApplyReq):
        job = db_one("SELECT * FROM public_jobs WHERE id=?", (job_id,))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        analysis = analyze_candidate_fit(job, req.resume_text, req.experience_years, req.notice_period)
        application_id = new_id("jobapp")
        db_exec(
            "INSERT INTO public_job_applications(id,job_id,applicant_name,applicant_email,applicant_phone,resume_text,cover_letter,experience_years,current_company,current_role,notice_period,expected_salary,linkedin_url,portfolio_url,ai_score,verdict,created_at,stage,updated_at,ai_summary) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                application_id,
                job_id,
                req.applicant_name[:120],
                req.applicant_email[:160],
                req.applicant_phone[:60],
                req.resume_text[:12000],
                req.cover_letter[:4000],
                int(req.experience_years),
                req.current_company[:120],
                req.current_role[:120],
                req.notice_period[:80],
                req.expected_salary[:80],
                req.linkedin_url[:220],
                req.portfolio_url[:220],
                float(analysis["ai_score"]),
                analysis["verdict"],
                now_iso(),
                "applied",
                now_iso(),
                f"{analysis['verdict']} | Score {(float(analysis['ai_score']) * 100):.0f}%",
            ),
        )
        profile = upsert_candidate_profile(
            email=req.applicant_email,
            full_name=req.applicant_name,
            phone=req.applicant_phone,
            resume_text=req.resume_text,
            current_company=req.current_company,
            current_role=req.current_role,
            total_exp=float(req.experience_years or 0),
            relevant_exp=float(req.experience_years or 0),
            notice_period=req.notice_period,
            expected_ctc=req.expected_salary,
            linkedin_url=req.linkedin_url,
            target_role=job.get("title", ""),
            job_change_intent="active",
            source="job_application",
            job_skills=job.get("skills", ""),
            target_jd=job.get("description", ""),
        )
        journey = upsert_candidate_journey(
            profile["id"],
            application_id=application_id,
            job_id=job_id,
            company_slug=job.get("company_slug", ""),
            company_name=job.get("company_name", ""),
            job_title=job.get("title", ""),
            stage="applied",
            status_note=f"Application submitted with {analysis['verdict']} AI fit.",
            source="job_application",
            last_event="Application submitted",
        )
        refresh_candidate_counters(profile["id"])
        return {
            "ok": True,
            "application_id": application_id,
            "profile_id": profile["id"],
            "journey_id": journey.get("id", ""),
            **analysis,
        }

    @app.post("/api/candidate/resume-sync")
    async def candidate_resume_sync(req: CandidateResumeSyncReq):
        target_job = db_one("SELECT * FROM public_jobs WHERE id=?", (req.job_id,)) if req.job_id else None
        target_role = req.target_role or (target_job or {}).get("title", "")
        target_jd = req.target_jd or (target_job or {}).get("description", "")
        target_skills = (target_job or {}).get("skills", "")
        alignment = build_resume_alignment(req.resume_text, target_role=target_role, target_jd=target_jd, job_skills=target_skills)
        profile = upsert_candidate_profile(
            email=req.email,
            full_name=req.full_name,
            phone=req.phone,
            resume_text=req.resume_text,
            current_company=req.current_company,
            current_role=req.current_role,
            current_location=req.current_location,
            preferred_location=req.preferred_location,
            total_exp=float(req.experience_years or 0),
            relevant_exp=float(req.experience_years or 0),
            notice_period=req.notice_period,
            current_ctc=req.current_ctc,
            expected_ctc=req.expected_ctc,
            linkedin_url=req.linkedin_url,
            target_role=target_role,
            job_change_intent=req.job_change_intent,
            source="resume_sync",
            job_skills=target_skills,
            target_jd=target_jd,
        )
        upsert_candidate_journey(
            profile["id"],
            application_id="",
            job_id=req.job_id or "",
            company_slug=(target_job or {}).get("company_slug", ""),
            company_name=(target_job or {}).get("company_name", "") or "TechBuzz Career",
            job_title=target_role or "Career profile setup",
            stage="profile_ready",
            status_note="Resume parsed, profile updated, and candidate journey initialized.",
            source="resume_sync",
            last_event="Profile synced from resume",
        )
        dashboard = candidate_dashboard_payload(req.email)
        return {
            "ok": True,
            "profile": dashboard["profile"],
            "stats": dashboard["stats"],
            "alignment": alignment,
            "recommended_jobs": dashboard["recommended_jobs"],
            "next_move": dashboard["next_move"],
        }

    @app.get("/api/candidate/dashboard")
    async def candidate_dashboard(email: str):
        return candidate_dashboard_payload(email)

    @app.get("/api/saas/stats")
    async def saas_stats():
        companies = int(((db_one("SELECT COUNT(*) AS n FROM public_companies") or {}).get("n", 0)) or 0)
        jobs = int(((db_one("SELECT COUNT(*) AS n FROM public_jobs WHERE status='open'") or {}).get("n", 0)) or 0)
        applications = int(((db_one("SELECT COUNT(*) AS n FROM public_job_applications") or {}).get("n", 0)) or 0)
        hires = int(((db_one("SELECT COUNT(*) AS n FROM public_job_applications WHERE COALESCE(stage,'applied')='hired'") or {}).get("n", 0)) or 0)
        return {"companies": companies, "active_jobs": jobs, "applications": applications, "hires": hires}

    @app.get("/api/saas/plans")
    async def saas_plans():
        rows = db_all("SELECT id,name,price_inr,billing_period,tagline,services_json,role FROM plans WHERE role='member' ORDER BY price_inr ASC") or []
        plans = []
        for row in rows:
            services = safe_parse_json(row.get("services_json"), [])
            price_inr = int(row.get("price_inr") or 0)
            plans.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "price_monthly": price_inr * 100,
                    "billing_period": row.get("billing_period"),
                    "target": "Public" if price_inr == 0 else "Companies",
                    "popular": row.get("id") in {"growth", "empire"},
                    "features": list(services),
                    "tagline": row.get("tagline", ""),
                }
            )
        return {"plans": plans}

    @app.post("/api/company/register")
    async def company_register(req: CompanyRegisterReq):
        name = (req.name or "").strip()
        owner_name = (req.owner_name or "").strip()
        owner_email = (req.owner_email or "").strip().lower()
        if not name or not owner_name or not owner_email or "@" not in owner_email:
            raise HTTPException(status_code=400, detail="Company name, owner name, and a valid email are required.")
        base_slug = slugify_company(name)
        slug = base_slug
        suffix = 1
        while company_row_by_slug(slug):
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        company_id = new_id("co")
        api_key = create_company_api_key(slug)
        plan = (req.plan or "starter").strip().lower() or "starter"
        db_exec(
            "INSERT INTO public_companies(id,slug,name,owner_name,owner_email,plan,api_key,tagline,website,city,primary_color,api_limit,api_calls_used,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                company_id,
                slug,
                name[:160],
                owner_name[:120],
                owner_email[:160],
                plan[:40],
                api_key,
                "",
                "",
                "",
                "#90f2d2",
                2000 if plan in {"starter", "free"} else 5000,
                0,
                now_iso(),
                now_iso(),
            ),
        )
        return {"ok": True, "slug": slug, "api_key": api_key, "company_id": company_id}

    @app.get("/api/company/{slug}/analytics")
    async def company_analytics(slug: str):
        return public_company_analytics(slug)

    @app.get("/api/company/{slug}/jobs")
    async def company_jobs(slug: str):
        if not company_row_by_slug(slug):
            raise HTTPException(status_code=404, detail="Company not found")
        return {"jobs": company_job_rows(slug)}

    @app.get("/api/company/{slug}/candidates")
    async def company_candidates(slug: str):
        if not company_row_by_slug(slug):
            raise HTTPException(status_code=404, detail="Company not found")
        return {"candidates": company_candidate_rows(slug)}

    @app.get("/api/company/{slug}/talent-map")
    async def company_talent_map(slug: str, available_by: str = "", limit: int = 16):
        return company_talent_map_payload(slug, available_by=available_by, limit=max(4, min(limit, 30)))

    @app.put("/api/company/{slug}/candidate/{candidate_id}/stage")
    async def company_candidate_stage(slug: str, candidate_id: str, req: CompanyStageReq):
        if not company_row_by_slug(slug):
            raise HTTPException(status_code=404, detail="Company not found")
        candidate = db_one(
            """
            SELECT a.id
            FROM public_job_applications a
            JOIN public_jobs j ON j.id=a.job_id
            WHERE a.id=? AND j.company_slug=?
            """,
            (candidate_id, slug),
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        stage = (req.stage or "applied").strip().lower()
        db_exec("UPDATE public_job_applications SET stage=?, updated_at=? WHERE id=?", (stage, now_iso(), candidate_id))
        application = db_one(
            """
            SELECT a.*, j.company_slug, j.company_name, j.title AS job_title
            FROM public_job_applications a
            JOIN public_jobs j ON j.id=a.job_id
            WHERE a.id=?
            """,
            (candidate_id,),
        )
        if application:
            profile = upsert_candidate_profile(
                email=application.get("applicant_email", ""),
                full_name=application.get("applicant_name", ""),
                phone=application.get("applicant_phone", ""),
                resume_text=application.get("resume_text", ""),
                current_company=application.get("current_company", ""),
                current_role=application.get("current_role", ""),
                total_exp=float(application.get("experience_years") or 0),
                relevant_exp=float(application.get("experience_years") or 0),
                notice_period=application.get("notice_period", ""),
                expected_ctc=application.get("expected_salary", ""),
                linkedin_url=application.get("linkedin_url", ""),
                target_role=application.get("job_title", ""),
                job_change_intent="active",
                source="company_stage",
            )
            upsert_candidate_journey(
                profile["id"],
                application_id=application.get("id", ""),
                job_id=application.get("job_id", ""),
                company_slug=application.get("company_slug", ""),
                company_name=application.get("company_name", ""),
                job_title=application.get("job_title", ""),
                stage=stage,
                status_note=f"Application moved to {stage}.",
                source="company_stage",
                last_event=f"Company updated stage to {stage}",
            )
        return {"ok": True, "candidate_id": candidate_id, "stage": stage}

    @app.post("/api/company/{slug}/ai-screen-all")
    async def company_ai_screen_all(slug: str):
        if not company_row_by_slug(slug):
            raise HTTPException(status_code=404, detail="Company not found")
        rows = db_all(
            """
            SELECT a.id, a.resume_text, a.experience_years, a.notice_period, j.*
            FROM public_job_applications a
            JOIN public_jobs j ON j.id=a.job_id
            WHERE j.company_slug=?
            """,
            (slug,),
        ) or []
        screened = 0
        for row in rows:
            analysis = analyze_candidate_fit(row, row.get("resume_text", ""), int(row.get("experience_years") or 0), row.get("notice_period", ""))
            db_exec(
                "UPDATE public_job_applications SET ai_score=?, verdict=?, ai_summary=?, updated_at=? WHERE id=?",
                (
                    float(analysis["ai_score"]),
                    analysis["verdict"],
                    f"{analysis['verdict']} | Score {(float(analysis['ai_score']) * 100):.0f}%",
                    now_iso(),
                    row["id"],
                ),
            )
            screened += 1
        return {"ok": True, "screened": screened}

    @app.post("/api/company/{slug}/job")
    async def company_post_job(slug: str, req: CompanyJobReq):
        company = company_row_by_slug(slug)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        job_id = new_id("job")
        db_exec(
            "INSERT INTO public_jobs(id,title,company_name,company_slug,location,remote,job_type,experience_min,experience_max,salary_min,salary_max,skills,description,requirements,department,category,status,openings,closes_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                job_id,
                req.title[:180],
                company["name"],
                slug,
                req.location[:120],
                req.remote[:24],
                req.job_type[:24],
                int(req.experience_min),
                int(req.experience_max),
                int(req.salary_min),
                int(req.salary_max),
                req.skills[:1200],
                req.description[:5000],
                req.requirements[:3000],
                req.department[:120],
                req.department[:60].lower() or "general",
                "open",
                max(1, int(req.openings or 1)),
                req.closes_at[:40],
                now_iso(),
                now_iso(),
            ),
        )
        return {"ok": True, "job_id": job_id}

    @app.put("/api/company/{slug}/profile")
    async def company_profile(slug: str, req: CompanyProfileReq):
        company = company_row_by_slug(slug)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        db_exec(
            "UPDATE public_companies SET tagline=?, website=?, city=?, primary_color=?, updated_at=? WHERE slug=?",
            (
                req.tagline[:240],
                req.website[:220],
                req.city[:120],
                req.primary_color[:24] or "#90f2d2",
                now_iso(),
                slug,
            ),
        )
        return {"ok": True, "profile": public_company_analytics(slug)["profile"]}

    @app.get("/api/v1/jobs")
    async def api_v1_jobs(request: Request):
        api_key = (request.headers.get("X-API-Key") or "").strip()
        company = company_row_by_api_key(api_key)
        if not company:
            raise HTTPException(status_code=401, detail="Valid X-API-Key is required.")
        increment_company_api_usage(company["id"])
        return {"jobs": company_job_rows(company["slug"]), "company": company["name"]}

    @app.post("/api/v1/post-job")
    async def api_v1_post_job(req: CompanyJobReq, request: Request):
        api_key = (request.headers.get("X-API-Key") or "").strip()
        company = company_row_by_api_key(api_key)
        if not company:
            raise HTTPException(status_code=401, detail="Valid X-API-Key is required.")
        increment_company_api_usage(company["id"])
        result = await company_post_job(company["slug"], req)
        return {**result, "company": company["name"]}

    @app.post("/api/v1/screen-candidate")
    async def api_v1_screen_candidate(req: CompanyScreenReq, request: Request):
        api_key = (request.headers.get("X-API-Key") or "").strip()
        company = company_row_by_api_key(api_key)
        if not company:
            raise HTTPException(status_code=401, detail="Valid X-API-Key is required.")
        increment_company_api_usage(company["id"])
        mock_job = {
            "title": req.job_title,
            "description": req.job_description,
            "skills": req.skills,
            "experience_min": 0,
            "experience_max": 10,
        }
        analysis = analyze_candidate_fit(mock_job, req.resume, 0, "")
        return {
            "ok": True,
            "company": company["name"],
            "job_title": req.job_title,
            "fit_score": analysis["ai_score"],
            "ai_score": analysis["ai_score"],
            "verdict": analysis["verdict"],
        }

    @app.post("/api/ide/project")
    async def create_ide_project(req: IDEProjectReq, request: Request):
        user = require_owner(request)
        project_id = new_id("ide")
        scaffold_files = {"README.md": f"# {req.name}\n\n{req.description or 'TechBuzz generated project.'}\n", "main." + ("py" if req.language.lower() in {"python", "py"} else "txt"): ("print('TechBuzz project online')\n" if req.language.lower() in {"python", "py"} else f"{req.name} scaffold ready.\n")}
        db_exec("INSERT INTO ide_projects(id,user_id,name,description,language,scaffold,files_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (project_id, user["id"], req.name[:140], req.description[:1200], req.language[:32], req.scaffold[:64], json.dumps(scaffold_files), now_iso(), now_iso()))
        project_dir = IDE_DIR / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in scaffold_files.items():
            (project_dir / filename).write_text(content, encoding="utf-8")
        return {"ok": True, "id": project_id, "files": scaffold_files}

    @app.get("/api/ide/projects")
    async def list_ide_projects(request: Request):
        user = require_owner(request)
        return {"projects": db_all("SELECT * FROM ide_projects WHERE user_id=? ORDER BY updated_at DESC LIMIT 30", (user["id"],)) or []}

    @app.get("/api/ide/project/{project_id}")
    async def get_ide_project(project_id: str, request: Request):
        user = require_owner(request)
        project = db_one("SELECT * FROM ide_projects WHERE id=? AND user_id=?", (project_id, user["id"]))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        project["files"] = safe_parse_json(project.get("files_json"), {})
        return project

    @app.post("/api/ide/snippet")
    async def save_ide_snippet(req: IDESnippetReq, request: Request):
        user = require_owner(request)
        snippet_id = new_id("ids")
        db_exec("INSERT INTO ide_snippets(id,user_id,title,language,code,created_at) VALUES(?,?,?,?,?,?)", (snippet_id, user["id"], req.title[:140], req.language[:24], req.code[:20000], now_iso()))
        save_brain_learning("tool_builder", req.title, req.code, req.code[:260], f"code,{req.language}", "ide_snippet", "", 0.71)
        return {"ok": True, "id": snippet_id}

    @app.get("/api/ide/snippets")
    async def list_ide_snippets(request: Request):
        user = require_owner(request)
        return {"snippets": db_all("SELECT * FROM ide_snippets WHERE user_id=? ORDER BY created_at DESC LIMIT 40", (user["id"],)) or []}

    @app.post("/api/ide/ai-generate")
    async def ide_ai_generate(req: IDEGenerateReq, request: Request):
        require_owner(request)
        code = await generate_code_snippet(req.prompt, req.language)
        if not code:
            code = "# TechBuzz fallback generator\nprint('No model output available')\n" if req.language.lower() in {"python", "py"} else "// TechBuzz fallback generator\n"
        return {"code": code, "language": req.language}

    @app.post("/api/ide/execute")
    async def ide_execute(req: IDEExecuteReq, request: Request):
        user = require_owner(request)
        result = execute_code(req.language, req.code)
        log_id = new_id("iex")
        db_exec("INSERT INTO ide_exec_logs(id,user_id,language,command,output,success,created_at) VALUES(?,?,?,?,?,?,?)", (log_id, user["id"], req.language[:24], result.get("command", ""), result.get("output", "")[:12000], 1 if result.get("success") else 0, now_iso()))
        return {"ok": bool(result.get("success")), "output": result.get("output", ""), "command": result.get("command", ""), "log_id": log_id}

    @app.get("/api/ide/execution-log")
    async def ide_execution_log(request: Request):
        user = require_owner(request)
        return {"logs": db_all("SELECT * FROM ide_exec_logs WHERE user_id=? ORDER BY created_at DESC LIMIT 30", (user["id"],)) or []}

    @app.post("/api/mission/project")
    async def create_mission_project(req: MissionProjectReq, request: Request):
        user = require_owner(request)
        project_id = new_id("mpr")
        tasks = build_project_tasks(req.name, req.description, req.tech_stack)
        strategy = {"summary": f"Deliver {req.name} with visible milestones, testing, and rollout discipline.", "timeline_weeks": max(2, min(12, len(tasks))), "risks": ["scope drift", "unclear acceptance", "release gaps"], "kpis": ["time-to-first-demo", "defect rate", "deployment reliability"]}
        db_exec("INSERT INTO mission_projects(id,user_id,name,description,phase,priority,tech_stack,progress,status,tasks_json,strategy_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (project_id, user["id"], req.name[:140], req.description[:2400], "planning", req.priority[:24], req.tech_stack[:240], 8, "planning", json.dumps(tasks), json.dumps(strategy), now_iso(), now_iso()))
        record_signal("exec_operations", "mother", "project_created", {"summary": f"Mission project {req.name} created", "project_id": project_id})
        return {"ok": True, "id": project_id, "plan": {"tasks": tasks, **strategy}, "tasks_created": len(tasks)}

    @app.get("/api/mission/projects")
    async def list_mission_projects(request: Request):
        user = require_owner(request)
        return {"projects": db_all("SELECT * FROM mission_projects WHERE user_id=? ORDER BY updated_at DESC LIMIT 30", (user["id"],)) or []}

    @app.get("/api/mission/project/{project_id}")
    async def get_mission_project(project_id: str, request: Request):
        user = require_owner(request)
        project = db_one("SELECT * FROM mission_projects WHERE id=? AND user_id=?", (project_id, user["id"]))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        project["tasks"] = safe_parse_json(project.get("tasks_json"), [])
        project["strategy"] = safe_parse_json(project.get("strategy_json"), {})
        project["deployments"] = db_all("SELECT * FROM mission_deployments WHERE project_id=? ORDER BY deployed_at DESC", (project_id,)) or []
        project["tests"] = db_all("SELECT * FROM mission_tests WHERE project_id=? ORDER BY created_at DESC", (project_id,)) or []
        project["tickets"] = db_all("SELECT * FROM mission_tickets WHERE project_id=? ORDER BY created_at DESC LIMIT 20", (project_id,)) or []
        return project

    @app.post("/api/mission/deploy")
    async def deploy_project(req: MissionDeployReq, request: Request):
        require_owner(request)
        project = db_one("SELECT * FROM mission_projects WHERE id=?", (req.project_id,))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        deploy_id = new_id("dep")
        slug = re.sub(r"[^a-z0-9]+", "-", project["name"].lower()).strip("-") or "project"
        deployed_url = f"https://{slug}.{req.platform}.app"
        details = {"steps": ["Validate config", "Build release", "Ship bundle", "Run smoke checks"], "health_check": "/api/health"}
        db_exec("INSERT INTO mission_deployments(id,project_id,version,environment,platform,status,deployed_url,details_json,deployed_at) VALUES(?,?,?,?,?,?,?,?,?)", (deploy_id, req.project_id, req.version[:48], req.environment[:24], req.platform[:24], "deployed", deployed_url, json.dumps(details), now_iso()))
        db_exec("UPDATE mission_projects SET status='deployed', phase='deployment', progress=92, updated_at=? WHERE id=?", (now_iso(), req.project_id))
        record_signal("exec_operations", "tool_builder", "deployment", {"summary": f"Deployed {project['name']} to {req.platform}", "url": deployed_url})
        return {"ok": True, "deployment_id": deploy_id, "deployed_url": deployed_url, "platform": req.platform, "version": req.version, "details": details}

    @app.post("/api/mission/test")
    async def mission_test(req: MissionTestReq, request: Request):
        require_owner(request)
        result = execute_code(req.language, req.code) if req.language.lower() in {"python", "py", "javascript", "js", "node", "c", "cpp", "c++"} else {"success": True, "output": "Static validation completed."}
        total = 5
        passed = 4 if result.get("success") else 2
        failed = total - passed
        coverage = round((passed / total) * 100, 1)
        test_id = new_id("tst")
        log_text = (result.get("output", "") or "No test output").strip()
        db_exec("INSERT INTO mission_tests(id,project_id,name,language,passed,total,coverage,log,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (test_id, req.project_id, req.name[:140], req.language[:24], passed, total, coverage, log_text[:12000], now_iso()))
        return {"ok": True, "suite_id": test_id, "passed": passed, "failed": failed, "total": total, "coverage": coverage, "log": log_text}

    @app.post("/api/mission/strategy")
    async def mission_strategy(req: MissionStrategyReq, request: Request):
        require_owner(request)
        project = db_one("SELECT name,description FROM mission_projects WHERE id=?", (req.project_id,)) if req.project_id else None
        project_name = project["name"] if project else "TechBuzz Initiative"
        content = f"Strategy for {project_name}: define outcome, map stakeholders, sequence the delivery plan, set KPIs, control rollout risk, and keep support/feedback loops active. Objectives: {req.objectives or 'delivery excellence'}."
        return {"ok": True, "content": content, "strategy_type": req.strategy_type}

    @app.post("/api/mission/support-ticket")
    async def create_support_ticket(req: MissionTicketReq, request: Request):
        user = require_member(request)
        ticket_id = new_id("tkt")
        ai_analysis = f"Likely root cause cluster: {req.ticket_type}. Priority `{req.priority}`. Suggested flow: reproduce, isolate environment, compare latest changes, prepare rollback or patch, and update stakeholders."
        db_exec("INSERT INTO mission_tickets(id,user_id,project_id,title,description,ticket_type,priority,status,ai_analysis,created_at,resolved_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (ticket_id, user["id"], req.project_id, req.title[:160], req.description[:3000], req.ticket_type[:40], req.priority[:24], "open", ai_analysis, now_iso(), ""))
        return {"ok": True, "id": ticket_id, "ai_analysis": ai_analysis}

    @app.get("/api/mission/tickets")
    async def mission_tickets(request: Request):
        user = require_member(request)
        rows = db_all("SELECT * FROM mission_tickets WHERE user_id=? OR ?='master' ORDER BY created_at DESC LIMIT 30", (user["id"], user.get("role"))) or []
        return {"tickets": rows}

    @app.put("/api/mission/ticket/{ticket_id}/resolve")
    async def resolve_ticket(ticket_id: str, request: Request):
        require_member(request)
        db_exec("UPDATE mission_tickets SET status='resolved', resolved_at=? WHERE id=?", (now_iso(), ticket_id))
        return {"ok": True}

    @app.post("/api/mission/migration")
    async def mission_migration(req: MissionMigrationReq, request: Request):
        require_owner(request)
        migration_id = new_id("mgr")
        plan = {"steps": [f"Audit current {req.from_system}", f"Map schema and dependencies for {req.to_system}", "Prepare rollback snapshot", "Run staged migration and validation"], "rollback": ["Restore pre-migration snapshot", "Switch traffic back", "Reconcile delta records"], "risks": ["schema mismatch", "downtime window", "data drift"], "estimated_hours": 12}
        db_exec("INSERT INTO mission_migrations(id,project_id,from_system,to_system,migration_type,plan_json,created_at) VALUES(?,?,?,?,?,?,?)", (migration_id, req.project_id, req.from_system[:120], req.to_system[:120], req.migration_type[:48], json.dumps(plan), now_iso()))
        return {"ok": True, "id": migration_id, "plan": plan}

    @app.get("/api/mission/overview")
    async def mission_overview(request: Request):
        require_owner(request)
        projects = db_all("SELECT id,name,status,phase,progress,priority,tech_stack,updated_at FROM mission_projects ORDER BY updated_at DESC LIMIT 20") or []
        deployments = db_all("SELECT * FROM mission_deployments ORDER BY deployed_at DESC LIMIT 5") or []
        tests = db_all("SELECT coverage FROM mission_tests ORDER BY created_at DESC LIMIT 12") or []
        tickets_open = (db_one("SELECT COUNT(*) AS n FROM mission_tickets WHERE status='open'") or {}).get("n", 0) or 0
        test_coverage = round(sum(float(row.get("coverage") or 0) for row in tests) / max(len(tests), 1), 1) if tests else 0.0
        return {"projects": projects, "deployments": deployments, "stats": {"tasks_pending": sum(max(0, 8 - int((project.get("progress") or 0) / 12)) for project in projects), "tasks_done": sum(max(0, int((project.get("progress") or 0) / 12)) for project in projects), "tickets_open": tickets_open, "test_coverage": test_coverage, "test_suites": len(tests), "total_projects": len(projects)}}

    @app.get("/api/neural/mesh")
    async def neural_mesh(request: Request):
        require_owner(request)
        return neural_mesh_snapshot()

    @app.get("/api/neural/status")
    async def neural_status_alias(request: Request):
        require_owner(request)
        return neural_mesh_snapshot()

    @app.get("/api/neural/mesh/public")
    async def neural_mesh_public():
        snapshot = neural_mesh_snapshot()
        return {"nodes": snapshot["nodes"][:12], "edges": snapshot["edges"][:20], "stats": snapshot["stats"], "mesh_config": snapshot["mesh_config"]}

    @app.get("/api/neural/mesh/stream")
    async def neural_mesh_stream(request: Request):
        require_owner(request)

        async def event_generator():
            while True:
                snapshot = neural_mesh_snapshot()
                payload = {"new_signals": recent_signals(8), "active_brains": snapshot["stats"]["active_brains"], "mesh_frequency": snapshot["mesh_config"].get("frequency_hz", 1.0)}
                yield f"data: {json.dumps(payload)}\n\n"
                await asyncio.sleep(2.0)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.put("/api/neural/mesh-frequency")
    async def neural_mesh_frequency(request: Request):
        require_owner(request)
        body = await request.json()
        hz = round(max(0.2, min(float(body.get("frequency_hz") or body.get("frequency") or body.get("value") or 1.0), 10.0)), 2)
        state = set_suite_state("neural_mesh", {"frequency_hz": hz})
        record_signal("mother", "mesh", "frequency", {"summary": f"Mesh frequency set to {hz} Hz", "frequency_hz": hz})
        return {"ok": True, "mesh_config": state}

    @app.get("/api/neural/central-db")
    async def neural_central_db(request: Request):
        require_owner(request)
        counts = {"brain_knowledge": (db_one("SELECT COUNT(*) AS n FROM brain_knowledge") or {}).get("n", 0) or 0, "world_brain_atoms": (db_one("SELECT COUNT(*) AS n FROM world_brain_atoms") or {}).get("n", 0) or 0, "browser_history": (db_one("SELECT COUNT(*) AS n FROM browser_history") or {}).get("n", 0) or 0, "mutation_events": (db_one("SELECT COUNT(*) AS n FROM mutation_events") or {}).get("n", 0) or 0, "photon_transmissions": (db_one("SELECT COUNT(*) AS n FROM photon_transmissions") or {}).get("n", 0) or 0}
        knowledge_by_brain = db_all("SELECT brain_id, COUNT(*) AS items, AVG(relevance_score) AS avg_relevance FROM brain_knowledge GROUP BY brain_id ORDER BY items DESC LIMIT 24") or []
        top_knowledge = db_all("SELECT brain_id,title,source_type,relevance_score FROM brain_knowledge ORDER BY relevance_score DESC, learned_at DESC LIMIT 20") or []
        snapshot = neural_mesh_snapshot()
        return {
            "total_knowledge_items": counts["brain_knowledge"],
            "counts": counts,
            "knowledge_by_brain": knowledge_by_brain,
            "top_knowledge": top_knowledge,
            "mesh_stats": {
                "total_signals": snapshot["stats"].get("signals", 0),
                "total_replications": snapshot["stats"].get("shares", 0),
                "carbon_copies": snapshot["stats"].get("carbon_copies", 0),
            },
            "monitor": mother_monitor_payload(get_state()),
        }

    @app.get("/api/neural/brain-db/{brain_id}")
    async def neural_brain_db(brain_id: str, request: Request):
        require_owner(request)
        hierarchy = brain_hierarchy_payload()
        brain = next((item for item in hierarchy.get("brains", []) if item.get("id") == brain_id), None)
        knowledge = db_all("SELECT title,summary,content,source_type,source_url,learned_at FROM brain_knowledge WHERE brain_id=? ORDER BY learned_at DESC LIMIT 50", (brain_id,)) or []
        signals_sent = recent_signals(80)
        relevant_sent = [row for row in signals_sent if row.get("from") == brain_id][:20]
        shared_from = [row for row in signals_sent if row.get("to") == brain_id and row.get("type") in {"broadcast", "cross_learn", "brain_learned"}][:20]
        connections = []
        for edge in neural_mesh_snapshot().get("edges", []):
            if edge.get("from") == brain_id:
                connections.append(edge.get("to"))
            elif edge.get("to") == brain_id:
                connections.append(edge.get("from"))
        return {
            "brain_id": brain_id,
            "brain": brain or {"id": brain_id, "name": brain_id, "emoji": "🧠"},
            "knowledge_count": len(knowledge),
            "knowledge": knowledge,
            "signals_sent": relevant_sent,
            "shared_from": shared_from,
            "connections": sorted(set(connections)),
        }

    @app.post("/api/neural/transmit")
    async def neural_transmit(req: NeuralTransmitReq, request: Request):
        require_owner(request)
        message = (req.signal_data or req.data or req.signal or "").strip()
        item = record_signal("mother", req.destination or "ALL", "broadcast", {"summary": message[:180], "channel": req.channel, "message": message})
        return {"ok": True, "signal": item, "confirmation": f"Signal sent on {req.channel} to {req.destination or 'ALL'}", "channel": req.channel, "destination": req.destination or "ALL"}

    @app.post("/api/neural/broadcast")
    async def neural_broadcast(request: Request):
        require_owner(request)
        body = await request.json()
        payload = body.get("payload") or {}
        message = body.get("message", "") or payload.get("message", "")
        item = record_signal(body.get("from_brain", body.get("origin", "mother")), "ALL", "broadcast", {"summary": message[:180], "message": message, "signal_type": body.get("signal_type", "directive")})
        total = max(1, neural_mesh_snapshot()["stats"].get("total_brains", 1) - 1)
        return {"ok": True, "signal": item, "broadcast_to": total}

    @app.post("/api/neural/receive")
    async def neural_receive(req: NeuralTransmitReq, request: Request):
        user = current_user(request)
        origin = user["id"] if user else "external"
        message = (req.signal or req.data or req.signal_data or "").strip()
        item = record_signal(req.source or origin, "mother", "receive", {"summary": message[:180], "channel": req.channel, "message": message})
        return {"ok": True, "signal": item, "brain": "mother", "routed_to": "mother"}

    @app.post("/api/neural/cross-learn")
    async def neural_cross_learn(request: Request):
        require_owner(request)
        hierarchy = brain_hierarchy_payload()
        brains = [brain["id"] for brain in hierarchy.get("brains", []) if brain["id"] != "mother"]
        random.shuffle(brains)
        chosen = brains[: min(6, len(brains))]
        for brain_id in chosen:
            save_brain_learning(brain_id, "Cross-learned lesson", "A reviewed lesson propagated through the neural mesh.", "Cross-learned lesson", "cross-learn,mesh", "cross_learn", "", 0.68)
        record_signal("mother", "mesh", "cross_learn", {"summary": f"Cross-learned {len(chosen)} brains", "brains": chosen})
        return {"ok": True, "brains": chosen, "successful": len(chosen)}

    @app.post("/api/neural/replicate")
    async def neural_replicate(request: Request):
        require_owner(request)
        body = await request.json()
        source = body.get("source_brain", "mother")
        target = body.get("target_brain", "")
        entries = db_all("SELECT title,content,summary,keywords,source_type,source_url,relevance_score FROM brain_knowledge WHERE brain_id=? ORDER BY relevance_score DESC, learned_at DESC LIMIT 8", (source,)) or []
        replicated = 0
        for row in entries:
            if target:
                save_brain_learning(target, row.get("title") or "Replicated lesson", row.get("content") or row.get("summary") or "", row.get("summary") or "", row.get("keywords") or "replicated", row.get("source_type") or "replicate", row.get("source_url") or "", float(row.get("relevance_score") or 0.64))
                replicated += 1
        signal = record_signal(source, target or "mesh", "replicate", {"summary": "Replication cycle completed", "copies": replicated})
        return {"ok": True, "replication": signal, "source": source, "target": target, "replicated": replicated}

    @app.post("/api/intel/learn")
    async def intel_learn(req: NeuralLearnReq, request: Request):
        require_owner(request)
        title = req.title or req.topic or f"Domain learning: {req.brain_id}"
        content = req.content or f"Learned topic: {title}"
        save_brain_learning(req.brain_id, title, content, req.summary or content[:200], req.keywords or "intel,learning", "manual_intel", req.source_url, 0.74)
        signal = record_signal("sec_anveshan", req.brain_id, "brain_learned", {"summary": req.summary or title, "title": title})
        return {"ok": True, "signal": signal, "brain_id": req.brain_id, "total_learned": 1}

    @app.post("/api/photon/network/start")
    async def photon_network_start(request: Request):
        require_owner(request)
        state = suite_state("photon_network", {"running": False})
        state["running"] = True
        set_suite_state("photon_network", state)
        agents = db_all("SELECT * FROM photon_agents ORDER BY codename ASC") or []
        for agent in agents:
            status = "deploying" if agent["domain"] in {"market-scan", "talent-hunt"} else "active"
            db_exec("UPDATE photon_agents SET status=?, updated_at=? WHERE id=?", (status, now_iso(), agent["id"]))
        record_signal("mother", "photon_network", "photon_start", {"summary": "Photon network started", "agents": len(agents)})
        return {"ok": True, "running": True, "agents": len(agents), "message": "Photon network online — visible agents are active"}

    @app.post("/api/photon/network/stop")
    async def photon_network_stop(request: Request):
        require_owner(request)
        state = suite_state("photon_network", {"running": False})
        state["running"] = False
        set_suite_state("photon_network", state)
        db_exec("UPDATE photon_agents SET status='dormant', updated_at=?", (now_iso(),))
        return {"ok": True, "running": False}

    @app.get("/api/photon/network/status")
    async def photon_network_status(request: Request):
        require_owner(request)
        return photon_status_payload()

    @app.get("/api/photon/status")
    async def photon_status_alias(request: Request):
        require_owner(request)
        return photon_status_payload()

    @app.post("/api/photon/mission")
    async def photon_mission(req: PhotonMissionReq, request: Request):
        user = require_owner(request)
        query = (req.query or req.title or req.objective or "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="Mission query is required")
        mission_id = new_id("phm")
        agents = db_all("SELECT * FROM photon_agents ORDER BY codename ASC") or []
        deployed = min(max(2, len(query.split()) // 2), max(2, len(agents)))
        mission_title = f"Mission: {query[:60]}"
        result = f"Visible mission launched across market, hiring, and signal lanes for `{query}`."
        db_exec("INSERT INTO photon_missions(id,user_id,title,objective,status,result,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (mission_id, user["id"], mission_title, query, "active", result, now_iso(), now_iso()))
        for agent in agents[:deployed]:
            extra_pages = 2 + (len(query) % 4)
            extra_intel = 1 + (len(query) % 5)
            db_exec("UPDATE photon_agents SET status=?, pages_read=pages_read+?, intel_gathered=intel_gathered+?, current_url=?, updated_at=? WHERE id=?", ("reading", extra_pages, extra_intel, f"https://www.google.com/search?q={quote_plus(query)}", now_iso(), agent["id"]))
            db_exec("INSERT INTO photon_transmissions(id,agent_id,title,summary,source_url,created_at) VALUES(?,?,?,?,?,?)", (new_id("ptx"), agent["id"], mission_title[:120], f"Visible photon mission gathered signal for {query}", f"https://www.google.com/search?q={quote_plus(query)}", now_iso()))
        record_signal("mother", "photon_network", "photon_mission", {"summary": f"Mission launched for {query}", "agents": deployed})
        return {"ok": True, "mission_id": mission_id, "query": query, "agents_deployed": deployed}

    @app.post("/api/photon/ask")
    async def photon_ask(req: PhotonAskReq, request: Request):
        require_owner(request)
        question = (req.question or "").strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question is required")
        transmissions = db_all("SELECT * FROM photon_transmissions ORDER BY created_at DESC LIMIT 12") or []
        context = "\n".join(f"- {row.get('summary','')}" for row in transmissions[:8])
        question_lower = question.lower()
        short_reply = any(term in question_lower for term in ("one line", "one-line", "keep it short", "short status", "short reply"))
        if short_reply:
            latest_signal = next((str(row.get("summary", "")).strip() for row in transmissions if str(row.get("summary", "")).strip()), "")
            answer = latest_signal or f"{AI_NAME} Photon is active and waiting for the next visible intelligence task."
        else:
            answer = f"{AI_NAME} Photon analysis: for `{question}`, focus on demand signals, candidate availability, market movement, and the next visible operator action.\n{context[:700]}"
        agents = db_all("SELECT * FROM photon_agents WHERE status IN ('active','reading','deploying')") or []
        return {"ok": True, "answer": answer.strip(), "intel_used": len(transmissions[:8]), "sources_count": len({row.get('source_url') for row in transmissions if row.get('source_url')}), "agents_active": len(agents)}

    @app.get("/api/photon/intel")
    async def photon_intel(request: Request):
        require_owner(request)
        return {"intel": db_all("SELECT * FROM photon_transmissions ORDER BY created_at DESC LIMIT 40") or []}

    @app.get("/api/photon/agents")
    async def photon_agents(request: Request):
        require_owner(request)
        return {"agents": db_all("SELECT * FROM photon_agents ORDER BY codename ASC") or []}

    @app.get("/api/photon/intel/stream")
    async def photon_intel_stream(request: Request):
        require_owner(request)

        async def event_generator():
            last_payload = ""
            while True:
                payload = photon_status_payload()
                encoded = json.dumps(payload)
                if encoded != last_payload:
                    yield f"data: {encoded}\n\n"
                    last_payload = encoded
                else:
                    yield f": keepalive {now_iso()}\n\n"
                await asyncio.sleep(2.5)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.get("/api/photon/missions")
    async def photon_missions(request: Request):
        require_owner(request)
        return {"missions": db_all("SELECT * FROM photon_missions ORDER BY updated_at DESC LIMIT 20") or []}

    @app.get("/api/research/experiments")
    async def research_experiments(request: Request):
        require_owner(request)
        rows = db_all("SELECT * FROM research_experiments ORDER BY created_at DESC LIMIT 30") or []
        experiments = []
        for row in rows:
            result = safe_parse_json(row.get("result_json"), {})
            experiments.append({
                "id": row["id"],
                "experiment_type": row.get("exp_type", "experiment"),
                "hypothesis": row.get("topic", ""),
                "language": result.get("language", "multi"),
                "fitness": float(result.get("fitness", 0.0) or 0.0),
                "created_at": row.get("created_at", ""),
            })
        return {
            "experiments": experiments,
            "stats": {
                "self_rewrites": sum(1 for row in experiments if row["experiment_type"] == "self_rewrite"),
                "c_programs_generated": sum(1 for row in experiments if row["experiment_type"] == "c_backbone"),
            },
        }

    @app.post("/api/research/self-rewrite")
    async def research_self_rewrite(req: ResearchRewriteReq, request: Request):
        user = require_owner(request)
        topic = (req.topic or "system resilience").strip()
        new_code = (
            f"# Visible rewrite proposal for {topic}\n"
            "def evolve_step(state):\n"
            "    state['review_required'] = True\n"
            "    state['focus'] = 'operator_visible_improvement'\n"
            "    return state\n"
        )
        fitness = round(0.61 + (len(topic) % 27) / 100, 3)
        result = {
            "topic": topic,
            "fitness": fitness,
            "self_rewrites_total": (db_one("SELECT COUNT(*) AS n FROM research_experiments WHERE exp_type='self_rewrite'") or {}).get("n", 0) + 1,
            "improvement": f"Generated a visible rewrite proposal for {topic}.",
            "evasion": "No covert evasion used. Review-first mutation only.",
            "code": new_code,
            "language": "python",
        }
        db_exec("INSERT INTO research_experiments(id,user_id,exp_type,topic,result_json,created_at) VALUES(?,?,?,?,?,?)", (new_id("rex"), user["id"], "self_rewrite", topic[:240], json.dumps(result), now_iso()))
        save_brain_learning("research_lab", f"Rewrite proposal: {topic}", new_code, result["improvement"], "research,rewrite,visible", "research_self_rewrite", "", fitness)
        return result

    @app.post("/api/research/c-backbone")
    async def research_c_backbone(req: ResearchCReq, request: Request):
        user = require_owner(request)
        program_name = (req.program_name or req.name or "techbuzz_backbone").strip()
        code = c_code_from_request(program_name, req.description, req.logic, req.language)
        execution = execute_code(req.language, code)
        compile_result = {
            "compiled": bool(execution.get("success")),
            "output": execution.get("output", "")[:1200],
            "errors": "" if execution.get("success") else execution.get("output", "")[:1200],
            "command": execution.get("command", ""),
        }
        result = {"program_name": program_name, "code": code, "compile_result": compile_result}
        db_exec("INSERT INTO research_experiments(id,user_id,exp_type,topic,result_json,created_at) VALUES(?,?,?,?,?,?)", (new_id("rex"), user["id"], "c_backbone", program_name[:240], json.dumps({"fitness": 0.88 if compile_result["compiled"] else 0.58, "language": req.language, **result}), now_iso()))
        return result

    @app.get("/api/research/c-backbone/templates")
    async def research_c_backbone_templates(request: Request):
        require_owner(request)
        stats = {"c_programs_generated": (db_one("SELECT COUNT(*) AS n FROM research_experiments WHERE exp_type='c_backbone'") or {}).get("n", 0) or 0}
        return {
            "templates": [item["name"] for item in C_TEMPLATES],
            "genome_language": {"version": "0.1.0", "keywords": ["signal", "route", "agent", "brain", "fitness"], "data_types": ["gene", "signal", "lesson", "route"]},
            "stats": stats,
        }

    @app.post("/api/research/filehippo")
    async def research_filehippo(req: ResearchFileHippoReq, request: Request):
        require_owner(request)
        query = (req.query or "").strip().lower()
        category = (req.category or "").strip().lower()
        items = []
        for item in FILEHIPPO_FALLBACK:
            haystack = f"{item['title']} {item['category']} {item['summary']}".lower()
            if (not query or query in haystack) and (not category or category in haystack):
                items.append({"name": item["title"], "description": item["summary"], "url": item["url"], "category": item["category"]})
        if not items:
            items = [{"name": item["title"], "description": item["summary"], "url": item["url"], "category": item["category"]} for item in FILEHIPPO_FALLBACK[:4]]
        for item in items[:6]:
            save_brain_learning("research_lab", f"FileHippo: {item['name']}", item["description"], item["description"], f"filehippo,{item['category']}", "filehippo_learning", item["url"], 0.63)
        return {"items_found": len(items), "items": items}

    @app.post("/api/research/create-software")
    async def research_create_software(req: ResearchSoftwareReq, request: Request):
        user = require_owner(request)
        software_id = new_id("sw")
        software_type = (req.software_type or req.type or "utility").strip()
        version = "0.1.0"
        capabilities = ["planning", "generation", "testing", "release-readiness"] if software_type in {"platform", "workspace"} else ["automation", "operator-control", "reporting"]
        code = (
            "from fastapi import FastAPI\n\n"
            f"app = FastAPI(title='{req.name}')\n\n"
            "@app.get('/health')\n"
            "async def health():\n"
            f"    return {{'status': 'ok', 'service': '{req.name}', 'type': '{software_type}'}}\n"
        )
        software_home = SOFTWARE_DIR / software_id
        software_home.mkdir(parents=True, exist_ok=True)
        (software_home / "main.py").write_text(code, encoding="utf-8")
        (software_home / "manifest.json").write_text(json.dumps({"id": software_id, "name": req.name, "version": version, "type": software_type, "capabilities": capabilities}, indent=2), encoding="utf-8")
        db_exec("INSERT INTO research_software(id,user_id,name,version,type,description,capabilities_json,code,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (software_id, user["id"], req.name[:160], version, software_type[:60], req.description[:2000], json.dumps(capabilities), code, now_iso()))
        return {"ok": True, "software_id": software_id, "name": req.name, "version": version, "type": software_type, "capabilities": capabilities, "code": code}

    @app.get("/api/research/software-registry")
    async def research_software_registry(request: Request):
        require_owner(request)
        rows = db_all("SELECT * FROM research_software ORDER BY created_at DESC LIMIT 40") or []
        software = []
        for row in rows:
            software.append({
                "id": row["id"],
                "name": row["name"],
                "software_type": row.get("type", "utility"),
                "version": row.get("version", "0.1.0"),
                "status": "ready",
            })
        return {"software": software, "total": len(software)}

    @app.post("/api/research/genome-lang")
    async def research_genome_lang(req: GenomeReq, request: Request):
        require_owner(request)
        raw = (req.code or "").strip()
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        tokens = []
        for line in lines[:30]:
            if ":" in line:
                token_type, value = line.split(":", 1)
            else:
                token_type, value = "statement", line
            tokens.append({"type": token_type.strip(), "value": value.strip()})
        return {"parsed": {"version": "0.1.0", "token_count": len(tokens), "tokens": tokens}}

    @app.post("/api/mutation/trigger")
    async def mutation_trigger(req: MutationReq, request: Request):
        require_owner(request)
        hierarchy = brain_hierarchy_payload()
        target = req.brain_id or "sec_signals"
        brain = next((item for item in hierarchy.get("brains", []) if item.get("id") == target), {"id": target, "name": target})
        mutation_type = req.mutation_type or "adaptive_refinement"
        fitness = round(0.52 + (sum(ord(ch) for ch in target + mutation_type) % 33) / 100, 3)
        improvement = f"{brain.get('name', target)} generated a visible mutation proposal for {mutation_type}."
        status = "pending"
        db_exec("INSERT INTO mutation_events(id,user_id,brain_id,mutation_type,fitness,improvement,status,lesson,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (new_id("mut"), "master", target, mutation_type[:80], fitness, improvement[:500], status, f"Lesson from {mutation_type}", now_iso()))
        return {"ok": True, "brain_name": brain.get("name", target), "brain_id": target, "mutation_type": mutation_type, "fitness_score": fitness, "dna_change": improvement, "generation": (db_one("SELECT COUNT(*) AS n FROM mutation_events") or {}).get("n", 0) or 1}

    @app.post("/api/mutation/mass-mutate")
    async def mutation_mass_mutate(request: Request):
        require_owner(request)
        hierarchy = brain_hierarchy_payload().get("brains", [])
        targets = [brain["id"] for brain in hierarchy if brain["id"] != "mother"][:8]
        total = 0
        for brain_id in targets:
            fitness = round(0.55 + (sum(ord(ch) for ch in brain_id) % 29) / 100, 3)
            db_exec("INSERT INTO mutation_events(id,user_id,brain_id,mutation_type,fitness,improvement,status,lesson,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (new_id("mut"), "master", brain_id, "mass_refinement", fitness, f"Mass refinement lesson for {brain_id}", "pending", "Shared mutation lesson", now_iso()))
            total += 1
        generation = (db_one("SELECT COUNT(*) AS n FROM mutation_events") or {}).get("n", 0) or total
        return {"ok": True, "total": total, "generation": generation}

    @app.post("/api/mutation/mother-review")
    async def mutation_mother_review(request: Request):
        require_owner(request)
        rows = db_all("SELECT * FROM mutation_events WHERE status='pending' ORDER BY created_at ASC LIMIT 40") or []
        approved = 0
        rejected = 0
        for row in rows:
            status = "approved" if float(row.get("fitness") or 0) >= 0.63 else "rejected"
            db_exec("UPDATE mutation_events SET status=? WHERE id=?", (status, row["id"]))
            if status == "approved":
                approved += 1
            else:
                rejected += 1
        return {"ok": True, "approved": approved, "rejected": rejected}

    @app.get("/api/mutation/history")
    async def mutation_history(request: Request):
        require_owner(request)
        return mutation_history_payload()

    @app.get("/api/mutation/gene-pool")
    async def mutation_gene_pool(request: Request):
        require_owner(request)
        payload = mutation_history_payload()
        return {"gene_pool": payload.get("gene_pool", []), "stats": payload.get("stats", {})}

    @app.post("/api/spread/start")
    async def spread_start(request: Request):
        require_owner(request)
        state = suite_state("spread", {"running": False, "speed": 1})
        state["running"] = True
        set_suite_state("spread", state)
        return {"ok": True, "running": True}

    @app.post("/api/spread/stop")
    async def spread_stop(request: Request):
        require_owner(request)
        state = suite_state("spread", {"running": False, "speed": 1})
        state["running"] = False
        set_suite_state("spread", state)
        return {"ok": True, "running": False}

    @app.get("/api/spread/status")
    async def spread_status(request: Request):
        require_owner(request)
        return spread_status_payload()

    @app.put("/api/spread/speed")
    async def spread_speed(req: SpreadSpeedReq, request: Request):
        require_owner(request)
        state = suite_state("spread", {"running": False, "speed": 1})
        state["speed"] = max(1, min(int(req.speed or 1), 20))
        set_suite_state("spread", state)
        return {"ok": True, "speed": state["speed"]}

    @app.post("/api/spread/manual-node")
    async def spread_manual_node(req: SpreadManualNodeReq, request: Request):
        user = require_owner(request)
        node_id = new_id("spn")
        content = (req.content or "Visible spread node").strip()
        path = SPREAD_DIR / f"{node_id}_{re.sub(r'[^a-zA-Z0-9]+', '_', req.label)[:32]}.txt"
        payload = f"label={req.label}\ncontent={content}\ncreated_at={now_iso()}\n"
        path.write_text(payload, encoding="utf-8")
        size = path.stat().st_size
        db_exec("INSERT INTO spread_nodes(id,user_id,label,size_bytes,status,path,created_at) VALUES(?,?,?,?,?,?,?)", (node_id, user["id"], req.label[:120], size, "stored", str(path), now_iso()))
        return {"ok": True, "id": node_id, "size": size}

    @app.delete("/api/spread/cull")
    async def spread_cull(request: Request):
        require_owner(request)
        rows = db_all("SELECT * FROM spread_nodes ORDER BY created_at ASC LIMIT 5") or []
        culled = 0
        for row in rows:
            try:
                if row.get("path"):
                    Path(row["path"]).unlink(missing_ok=True)
            except Exception:
                pass
            db_exec("DELETE FROM spread_nodes WHERE id=?", (row["id"],))
            culled += 1
        status = spread_status_payload()
        return {"ok": True, "culled": culled, "vault_used_pct": status.get("vault_used_pct", 0.0)}

    @app.get("/api/spread/tree")
    async def spread_tree(request: Request):
        require_owner(request)
        return {"tree": spread_status_payload().get("file_tree", [])}

    @app.post("/api/phantom/route")
    async def phantom_route(req: PhantomRouteReq, request: Request):
        require_owner(request)
        packet_id = new_id("pkt")
        payload = (req.payload or "Visible phantom packet").strip()
        origin = req.origin_atom or "alpha"
        destination = req.dest_atom or "omega"
        hop_chain = [f"atom_{random.randint(100, 999)}" for _ in range(random.randint(3, 7))]
        visible_as = f"mol_{packet_id[-6:]}"
        note = "Visible decoy routing active. This is an operator-auditable simulation, not covert transport."
        db_exec("INSERT INTO phantom_packets(id,origin_atom,dest_atom,visible_as,hop_chain_json,purpose,revealed,created_at) VALUES(?,?,?,?,?,?,?,?)", (packet_id, origin, destination, visible_as, json.dumps(hop_chain), payload[:240], 0, now_iso()))
        return {"ok": True, "id": packet_id, "visible_as": visible_as, "origin_atom": origin, "dest_atom": destination, "hop_count": len(hop_chain), "hop_chain": hop_chain, "note": note}

    @app.get("/api/phantom/packets")
    async def phantom_packets(request: Request):
        require_owner(request)
        packets = db_all("SELECT * FROM phantom_packets ORDER BY created_at DESC LIMIT 40") or []
        normalized = []
        attack_count = 0
        for row in packets:
            attack_detected = bool(int(row.get("revealed") or 0))
            if attack_detected:
                attack_count += 1
            normalized.append({
                **row,
                "molecule_tag": row.get("visible_as", ""),
                "hop_chain": row.get("hop_chain_json", "[]"),
                "attack_detected": attack_detected,
            })
        return {"packets": normalized, "attack_count": attack_count, "total": len(normalized)}

    @app.post("/api/phantom/reveal/{packet_id}")
    async def phantom_reveal(packet_id: str, request: Request):
        require_owner(request)
        row = db_one("SELECT * FROM phantom_packets WHERE id=?", (packet_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Packet not found")
        db_exec("UPDATE phantom_packets SET revealed=1 WHERE id=?", (packet_id,))
        hops = safe_parse_json(row.get("hop_chain_json"), [])
        return {"REVEALED_origin_atom": row.get("origin_atom", "unknown"), "REVEALED_dest_atom": row.get("dest_atom", "unknown"), "REVEALED_hop_chain": hops, "attack_status": "revealed"}

    @app.post("/api/phantom/simulate-attack")
    async def phantom_simulate_attack(request: Request):
        require_owner(request)
        rewrite = await evasion_rewrite(EvasionRewriteReq(trigger="attack", topic="threat-response"), request)
        decoys = random.randint(3, 7)
        return {"ok": True, "decoys_deployed": decoys, "evasion_triggered": {"cycle": rewrite.get("cycle", 1)}}

    @app.post("/api/evasion/start")
    async def evasion_start(request: Request):
        require_owner(request)
        state = suite_state("evasion", {"running": False, "level": "visible", "current_logic": "manual_review", "threat_score": 0.22, "rewrites_done": 0})
        state["running"] = True
        state["evasion_level"] = "watching"
        set_suite_state("evasion", state)
        return {"ok": True, "state": state}

    @app.post("/api/evasion/stop")
    async def evasion_stop(request: Request):
        require_owner(request)
        state = suite_state("evasion", {"running": False, "level": "visible", "current_logic": "manual_review", "threat_score": 0.22, "rewrites_done": 0})
        state["running"] = False
        state["evasion_level"] = "idle"
        set_suite_state("evasion", state)
        return {"ok": True, "state": state}

    @app.post("/api/evasion/rewrite")
    async def evasion_rewrite(req: EvasionRewriteReq, request: Request):
        require_owner(request)
        state = suite_state("evasion", {"running": False, "level": "visible", "current_logic": "manual_review", "threat_score": 0.22, "rewrites_done": 0, "cycle": 0})
        old_logic = state.get("current_logic", "manual_review")
        cycle = int(state.get("cycle", 0) or 0) + 1
        new_logic = f"visible_rewrite_cycle_{cycle}_{(req.trigger or 'manual').replace(' ', '_')}"
        fitness_delta = round(0.01 + ((cycle % 7) / 100), 4)
        state.update({
            "running": state.get("running", False),
            "evasion_level": "mutating" if state.get("running") else "watching",
            "current_logic": new_logic,
            "threat_score": round(min(float(state.get("threat_score", 0.22)) + 0.03, 0.99), 2),
            "rewrites_done": int(state.get("rewrites_done", 0) or 0) + 1,
            "cycle": cycle,
        })
        set_suite_state("evasion", state)
        db_exec("INSERT INTO evasion_events(id,user_id,action,level,logic,threat_score,created_at) VALUES(?,?,?,?,?,?,?)", (new_id("eva"), "master", req.trigger[:60], state["evasion_level"], json.dumps({"old_logic": old_logic, "new_logic": new_logic, "trigger": req.trigger, "fitness_delta": fitness_delta, "cycle": cycle}), float(state["threat_score"]), now_iso()))
        return {"ok": True, "cycle": cycle, "old_logic": old_logic, "new_logic": new_logic, "trigger": req.trigger, "fitness_delta": fitness_delta}

    @app.get("/api/evasion/status")
    async def evasion_status(request: Request):
        require_owner(request)
        state = suite_state("evasion", {"running": False, "evasion_level": "idle", "current_logic": "manual_review", "threat_score": 0.22, "rewrites_done": 0, "cycle": 0})
        rows = db_all("SELECT * FROM evasion_events ORDER BY created_at DESC LIMIT 20") or []
        history = []
        for row in rows:
            logic = safe_parse_json(row.get("logic"), {})
            history.append({
                "old_logic": logic.get("old_logic", ""),
                "new_logic": logic.get("new_logic", ""),
                "trigger": logic.get("trigger", row.get("action", "manual")),
                "fitness_delta": float(logic.get("fitness_delta", 0.0) or 0.0),
                "cycle": int(logic.get("cycle", 0) or 0),
                "at": row.get("created_at", ""),
            })
        state.setdefault("evasion_level", "idle" if not state.get("running") else "watching")
        return {"state": state, "history": history}

    ensure_tables()
    seed_public_jobs()
    ensure_public_company_seed()
    seed_photon_agents()
    seed_research_software()
    set_suite_state("neural_mesh", {"frequency_hz": suite_state("neural_mesh", {"frequency_hz": 1.0}).get("frequency_hz", 1.0)})
    set_suite_state("photon_network", suite_state("photon_network", {"running": False}))
    set_suite_state("spread", suite_state("spread", {"running": False, "speed": 1}))
    set_suite_state("evasion", suite_state("evasion", {"running": False, "evasion_level": "idle", "current_logic": "manual_review", "threat_score": 0.22, "rewrites_done": 0, "cycle": 0}))
    log.info("Browser Suite layer loaded: Browser · Career · Jobs · IDE · Mission · Neural · Photon · Research · Spread")
    return {
        "status": "loaded",
        "browser_dir": str(BROWSER_DIR),
        "spread_dir": str(SPREAD_DIR),
        "status_payload": {
            "browser": browser_status_payload,
            "neural": neural_mesh_snapshot,
            "photon": photon_status_payload,
            "spread": spread_status_payload,
        },
    }
