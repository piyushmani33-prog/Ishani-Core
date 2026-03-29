import json
import re
from typing import Any, Dict, List

from fastapi import HTTPException, Request

try:
    import pycountry  # type: ignore
except Exception:
    pycountry = None


WORLD_ATLAS_DOMAINS: List[Dict[str, str]] = [
    {"id": "geography", "title": "World Geography And Region Mapping", "summary": "Track country, region, and location context for recruiting."},
    {"id": "population", "title": "Population And Demographic Bands", "summary": "Use demographic scale as context, but verify exact numbers live."},
    {"id": "work_culture", "title": "Work Culture And People Behaviour", "summary": "Understand pace, hierarchy, flexibility, and communication without stereotyping."},
    {"id": "language", "title": "Language And Communication", "summary": "Respect local language, business English, and multilingual realities."},
    {"id": "culture", "title": "Culture, Religion, And Social Context", "summary": "Recognize calendars, norms, and context without unfair filtering."},
    {"id": "rights", "title": "Gender, Rights, And Inclusion", "summary": "Protect equal opportunity and candidate dignity."},
    {"id": "law", "title": "Rules, Labor Law, And Compliance", "summary": "Treat exact law and district obligations as live-check data."},
    {"id": "government_jobs", "title": "Government Jobs And Public Hiring", "summary": "Understand grades, exams, and official hiring bodies."},
    {"id": "private_jobs", "title": "Private Jobs And Corporate Hiring", "summary": "Map startup, SMB, enterprise, consulting, GCC, and sector hiring."},
    {"id": "sourcing", "title": "Sourcing And Market Mapping", "summary": "Search by geography, role family, company archetype, and intent."},
    {"id": "screening", "title": "Screening, Evidence, And Fit", "summary": "Separate total experience, relevant experience, fit, and risk."},
    {"id": "interviewing", "title": "Interviewing And Evaluation", "summary": "Use structured scorecards and comparable evidence."},
    {"id": "candidate_state", "title": "Candidate Movement And Intent", "summary": "Track notice state, active/passive intent, and job-change motives."},
    {"id": "capability", "title": "Capability Ladder And Potential", "summary": "Assess what a person can learn, build, manage, lead, or architect."},
]

WORLD_ATLAS_REGIONS: List[Dict[str, str]] = [
    {"id": "global", "title": "Global Layer", "summary": "Cross-border recruiting and distributed delivery."},
    {"id": "south_asia", "title": "South Asia", "summary": "High talent density and notice-period driven movement."},
    {"id": "east_southeast_asia", "title": "East And Southeast Asia", "summary": "Strong platform, manufacturing, and services talent."},
    {"id": "middle_east_africa", "title": "Middle East And Africa", "summary": "Mobility, localization, and public/private hiring mix."},
    {"id": "europe", "title": "Europe", "summary": "Rights-heavy frameworks and multilingual recruiting."},
    {"id": "north_america", "title": "North America", "summary": "Fast private hiring and high specialization."},
    {"id": "latin_america", "title": "Latin America", "summary": "Nearshore, bilingual, and remote-friendly talent lanes."},
    {"id": "oceania", "title": "Oceania", "summary": "Smaller high-value markets with strong compliance checks."},
]

WORLD_ROLE_FAMILIES: List[Dict[str, str]] = [
    {"id": "software", "title": "Software Engineering"},
    {"id": "data_ai", "title": "Data, AI, And Analytics"},
    {"id": "cloud_devops", "title": "Cloud, DevOps, And Security"},
    {"id": "product_design", "title": "Product And Design"},
    {"id": "sales_marketing", "title": "Sales And Marketing"},
    {"id": "finance_accounts", "title": "Finance And Accounts"},
    {"id": "hr_talent", "title": "HR And Talent"},
    {"id": "operations_supply", "title": "Operations And Supply Chain"},
    {"id": "manufacturing_quality", "title": "Manufacturing And Quality"},
    {"id": "healthcare_lifesciences", "title": "Healthcare And Life Sciences"},
    {"id": "legal_compliance", "title": "Legal And Compliance"},
    {"id": "public_sector", "title": "Government And Public Sector"},
]

WORLD_CANDIDATE_AXES: List[Dict[str, str]] = [
    {"id": "total_experience", "title": "Total Experience"},
    {"id": "relevant_experience", "title": "Relevant Experience"},
    {"id": "notice_serving", "title": "Serving Notice"},
    {"id": "notice_not_serving", "title": "Not Serving Notice"},
    {"id": "immediate_joiner", "title": "Immediate Joiner"},
    {"id": "active_candidate", "title": "Active Candidate"},
    {"id": "passive_candidate", "title": "Passive Candidate"},
    {"id": "job_change_reason", "title": "Reasons For Job Change"},
    {"id": "next_job_expectation", "title": "Next Job Expectations"},
    {"id": "lifestyle_fit", "title": "Lifestyle And Life-Stage Fit"},
    {"id": "learning_capacity", "title": "Learning Capacity"},
    {"id": "builder_capacity", "title": "Builder Capacity"},
    {"id": "manager_capacity", "title": "Manager Capacity"},
    {"id": "leader_capacity", "title": "Leader Capacity"},
    {"id": "architect_capacity", "title": "Architect Capacity"},
    {"id": "memory_and_judgment", "title": "Thinking, Memory, And Judgment"},
]

WORLD_SKILL_BUNDLES: List[Dict[str, str]] = [
    {"id": "backend_cloud", "title": "Backend + Cloud"},
    {"id": "frontend_product", "title": "Frontend + Product Thinking"},
    {"id": "data_ml_ops", "title": "Data + ML + Ops"},
    {"id": "devops_security", "title": "DevOps + Security"},
    {"id": "sales_solutioning", "title": "Sales + Solutioning"},
    {"id": "finance_systems", "title": "Finance + Systems"},
    {"id": "hr_analytics", "title": "HR + Analytics"},
    {"id": "product_design_research", "title": "Product + Design + Research"},
    {"id": "ops_procurement", "title": "Operations + Procurement"},
    {"id": "public_policy_delivery", "title": "Public Policy + Delivery"},
]

WORLD_SOURCE_PACKS: List[Dict[str, str]] = [
    {"id": "world_bank", "title": "World Bank Data", "url": "https://data.worldbank.org/", "scope": "population, macro, labor", "authority": "official_data"},
    {"id": "undata", "title": "UNData", "url": "https://data.un.org/", "scope": "country and population data", "authority": "official_data"},
    {"id": "ilo", "title": "ILOSTAT", "url": "https://ilostat.ilo.org/", "scope": "labor, employment, wages", "authority": "official_data"},
    {"id": "oecd", "title": "OECD Employment", "url": "https://www.oecd.org/employment/", "scope": "advanced labor-market patterns", "authority": "official_data"},
    {"id": "eurostat", "title": "Eurostat Labour", "url": "https://ec.europa.eu/eurostat", "scope": "European labor and mobility", "authority": "official_data"},
    {"id": "labor_ministry", "title": "Labor Ministries", "url": "https://www.ilo.org/global/lang--en/index.htm", "scope": "labor law and rights", "authority": "official_law"},
    {"id": "public_service", "title": "Public Service Commissions", "url": "https://www.upsc.gov.in/", "scope": "government jobs and grades", "authority": "official_hiring"},
    {"id": "tax_authorities", "title": "Tax Authorities", "url": "https://www.oecd.org/tax/", "scope": "local tax and payroll obligations", "authority": "official_compliance"},
]

FALLBACK_COUNTRY_NAMES: List[str] = [
    "Argentina", "Australia", "Austria", "Bangladesh", "Belgium", "Brazil", "Canada", "Chile", "China", "Colombia",
    "Czechia", "Denmark", "Egypt", "Finland", "France", "Germany", "Ghana", "Greece", "Hong Kong", "Hungary",
    "India", "Indonesia", "Ireland", "Israel", "Italy", "Japan", "Kenya", "Malaysia", "Mexico", "Morocco",
    "Netherlands", "New Zealand", "Nigeria", "Norway", "Pakistan", "Peru", "Philippines", "Poland", "Portugal", "Qatar",
    "Romania", "Saudi Arabia", "Singapore", "South Africa", "South Korea", "Spain", "Sri Lanka", "Sweden", "Switzerland", "Taiwan",
    "Thailand", "Turkey", "UAE", "United Kingdom", "United States", "Vietnam",
]


def install_global_recruitment_brain_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_one = ctx["db_one"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    brain_hierarchy_payload = ctx["brain_hierarchy_payload"]

    def require_session(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")
        return user

    def country_registry() -> List[str]:
        if pycountry is not None:
            names = sorted(
                {
                    (getattr(country, "official_name", None) or country.name).strip()
                    for country in pycountry.countries
                    if getattr(country, "name", None)
                }
            )
            if names:
                return names
        return FALLBACK_COUNTRY_NAMES

    def subdivision_count() -> int:
        try:
            return len(list(pycountry.subdivisions)) if pycountry is not None else 0
        except Exception:
            return 0

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS world_brain_atoms(
                id TEXT PRIMARY KEY,
                atom_key TEXT UNIQUE,
                domain TEXT,
                geo_scope TEXT,
                lens TEXT,
                title TEXT,
                summary TEXT,
                content TEXT,
                tags_json TEXT,
                source_type TEXT,
                source_url TEXT,
                relevance_score REAL DEFAULT 0.8,
                created_at TEXT
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS world_brain_sources(
                id TEXT PRIMARY KEY,
                source_key TEXT UNIQUE,
                title TEXT,
                url TEXT,
                scope TEXT,
                authority TEXT,
                created_at TEXT
            )
            """
        )

    def upsert_atom(
        atom_key: str,
        domain: str,
        geo_scope: str,
        lens: str,
        title: str,
        summary: str,
        content: str,
        tags: List[str],
        source_type: str = "atlas_seed",
        source_url: str = "",
        relevance_score: float = 0.86,
    ) -> None:
        if db_one("SELECT id FROM world_brain_atoms WHERE atom_key=?", (atom_key,)):
            return
        db_exec(
            """
            INSERT INTO world_brain_atoms(
                id,atom_key,domain,geo_scope,lens,title,summary,content,tags_json,source_type,source_url,relevance_score,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                new_id("wba"),
                atom_key,
                domain,
                geo_scope,
                lens,
                title,
                summary[:500],
                content[:4000],
                json.dumps(tags, ensure_ascii=False),
                source_type,
                source_url,
                relevance_score,
                now_iso(),
            ),
        )

    def seed_sources() -> None:
        for source in WORLD_SOURCE_PACKS:
            if db_one("SELECT id FROM world_brain_sources WHERE source_key=?", (source["id"],)):
                continue
            db_exec(
                """
                INSERT INTO world_brain_sources(id,source_key,title,url,scope,authority,created_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    new_id("wbs"),
                    source["id"],
                    source["title"],
                    source["url"],
                    source["scope"],
                    source["authority"],
                    now_iso(),
                ),
            )

    def seed_world_atoms() -> None:
        for domain in WORLD_ATLAS_DOMAINS:
            upsert_atom(
                f"domain::{domain['id']}",
                domain["id"],
                "global",
                "always_remember",
                domain["title"],
                domain["summary"],
                (
                    f"{domain['summary']} "
                    "This is permanent baseline recruitment knowledge. Verify live laws, rights, grades, and exact statistics from official sources before claiming they are current."
                ),
                [domain["id"], "global", "always_remember", "recruitment"],
                relevance_score=0.99,
            )
        for region in WORLD_ATLAS_REGIONS:
            upsert_atom(
                f"region::{region['id']}",
                "geography",
                region["id"],
                "regional_context",
                region["title"],
                region["summary"],
                (
                    f"{region['summary']} "
                    "Recruiting in this region should account for language fit, time zone, work authorization, compensation norms, mobility, and communication style."
                ),
                [region["id"], "region", "global_hiring"],
                relevance_score=0.95,
            )
        for family in WORLD_ROLE_FAMILIES:
            upsert_atom(
                f"role_family::{family['id']}",
                "private_jobs",
                "global",
                "role_family",
                family["title"],
                f"{family['title']} is a permanent role-family lane in the recruitment atlas.",
                (
                    f"{family['title']} should be evaluated through outcomes, niche signals, adjacent skills, and execution proof rather than title-matching alone."
                ),
                [family["id"], "role_family", "jobs"],
                relevance_score=0.93,
            )
        for axis in WORLD_CANDIDATE_AXES:
            upsert_atom(
                f"candidate_axis::{axis['id']}",
                "candidate_state",
                "global",
                "candidate_axis",
                axis["title"],
                f"{axis['title']} is a permanent candidate-intelligence dimension.",
                (
                    f"{axis['title']} should be tracked as structured evidence in recruiting decisions, not as guesswork or vague intuition."
                ),
                [axis["id"], "candidate", "screening"],
                relevance_score=0.94,
            )
        for bundle in WORLD_SKILL_BUNDLES:
            upsert_atom(
                f"skill_bundle::{bundle['id']}",
                "sourcing",
                "global",
                "combined_skills",
                bundle["title"],
                f"{bundle['title']} is a recurring hybrid skill cluster.",
                (
                    f"{bundle['title']} should be used as a sourcing and screening anchor for niche or hybrid roles where isolated keywords are too weak."
                ),
                [bundle["id"], "combined_skills", "hybrid_roles"],
                relevance_score=0.92,
            )
        for name in country_registry():
            country_key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            upsert_atom(
                f"country::{country_key}",
                "geography",
                "country",
                "country_registry",
                f"Country Node: {name}",
                f"{name} is preserved as a country-level node in the global hiring atlas.",
                (
                    f"{name} should be treated as a distinct hiring context. Before making claims about population, rights, labor law, government grades, quotas, or district rules, use official live sources."
                ),
                [name.lower(), "country", "global_map", "live_check"],
                source_type="country_seed",
                relevance_score=0.88,
            )
        for family in WORLD_ROLE_FAMILIES:
            for bundle in WORLD_SKILL_BUNDLES:
                for axis in WORLD_CANDIDATE_AXES[:8]:
                    upsert_atom(
                        f"combo::{family['id']}::{bundle['id']}::{axis['id']}",
                        "screening",
                        "global",
                        "role_candidate_combo",
                        f"{family['title']} x {bundle['title']} x {axis['title']}",
                        f"Use this combo to evaluate {family['title'].lower()} candidates when {axis['title'].lower()} matters.",
                        (
                            f"For {family['title'].lower()} hiring, combine {bundle['title'].lower()} with the candidate signal {axis['title'].lower()} to separate keyword overlap from real delivery fit."
                        ),
                        [family["id"], bundle["id"], axis["id"], "combo"],
                        relevance_score=0.84,
                    )

    def broadcast_world_references() -> None:
        references = [
            {
                "title": "Global Hiring Atlas",
                "summary": "Permanent world map of regions, countries, role families, and candidate-intelligence dimensions.",
                "keywords": ["world", "atlas", "regions", "countries", "global_hiring"],
            },
            {
                "title": "Live Law And Rights Retrieval Rule",
                "summary": "Exact laws, rights, quotas, district rules, and public-service grades must be verified from official live sources before claiming they are current.",
                "keywords": ["law", "rights", "compliance", "live_check", "official_sources"],
            },
            {
                "title": "Candidate Intent And Capability Lattice",
                "summary": "Always evaluate total experience, relevant experience, notice state, active/passive intent, learning, building, managing, leading, and architecting potential.",
                "keywords": ["candidate", "experience", "notice", "active", "passive", "capability"],
            },
        ]
        for brain in brain_hierarchy_payload().get("brains", []):
            for ref in references:
                if db_one(
                    """
                    SELECT id FROM brain_knowledge
                    WHERE brain_id=? AND source_type='world_atlas_seed' AND title=?
                    """,
                    (brain["id"], ref["title"]),
                ):
                    continue
                db_exec(
                    """
                    INSERT INTO brain_knowledge(id,brain_id,source_type,source_url,title,content,summary,keywords,relevance_score,learned_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        new_id("know"),
                        brain["id"],
                        "world_atlas_seed",
                        "world://atlas",
                        ref["title"],
                        f"Brain: {brain['name']}\nLayer: {brain.get('layer', 'tool')}\nPermanent memory: {ref['summary']}",
                        ref["summary"],
                        json.dumps(ref["keywords"], ensure_ascii=False),
                        0.91,
                        now_iso(),
                    ),
                )

    def search_world_atoms(query: str, limit: int = 8) -> List[Dict[str, Any]]:
        rows = db_all(
            """
            SELECT title, summary, geo_scope, domain, lens, tags_json, source_type, source_url, relevance_score
            FROM world_brain_atoms
            ORDER BY relevance_score DESC, created_at DESC
            LIMIT 1600
            """
        ) or []
        tokens = [token for token in re.findall(r"[a-z0-9_+.-]{3,}", (query or "").lower()) if token]
        if not tokens:
            return rows[:limit]
        scored: List[Dict[str, Any]] = []
        for row in rows:
            haystack = " ".join(
                [
                    str(row.get("title", "")),
                    str(row.get("summary", "")),
                    str(row.get("geo_scope", "")),
                    str(row.get("domain", "")),
                    str(row.get("lens", "")),
                    str(row.get("tags_json", "")),
                ]
            ).lower()
            score = sum(1 for token in tokens if token in haystack)
            if score:
                item = dict(row)
                item["_score"] = score + float(row.get("relevance_score", 0) or 0)
                scored.append(item)
        scored.sort(key=lambda item: item.get("_score", 0), reverse=True)
        return scored[:limit]

    def relevant_sources(query: str, limit: int = 4) -> List[Dict[str, Any]]:
        rows = db_all(
            """
            SELECT title, url, scope, authority
            FROM world_brain_sources
            ORDER BY title
            """
        ) or []
        q = (query or "").lower()
        if any(term in q for term in ("law", "rights", "rule", "district", "state", "government", "grade", "quota", "tax", "population")):
            narrowed = [row for row in rows if row.get("authority") in {"official_law", "official_hiring", "official_compliance", "official_data"}]
            return narrowed[:limit] or rows[:limit]
        return rows[:limit]

    def context_brief(query: str, limit: int = 8) -> str:
        atoms = search_world_atoms(query, limit=limit)
        lines = [f"- {row.get('title')}: {row.get('summary')}" for row in atoms]
        q = (query or "").lower()
        if any(term in q for term in ("law", "rights", "population", "government", "rule", "district", "state")):
            lines.extend([f"- Live official source: {row['title']} ({row['scope']})" for row in relevant_sources(query, limit=3)])
            lines.append("- Exact laws, rights, quotas, grades, and district rules must be checked live before claiming they are current.")
        return "\n".join(lines[: limit + 4]) if lines else "- Global atlas is still loading."

    def status_payload() -> Dict[str, Any]:
        atom_count = (db_one("SELECT COUNT(*) AS count FROM world_brain_atoms") or {}).get("count", 0) or 0
        source_count = (db_one("SELECT COUNT(*) AS count FROM world_brain_sources") or {}).get("count", 0) or 0
        country_count = len(country_registry())
        possible_thoughts = (
            max(country_count, 1)
            * max(len(WORLD_ATLAS_DOMAINS), 1)
            * max(len(WORLD_ROLE_FAMILIES), 1)
            * max(len(WORLD_CANDIDATE_AXES), 1)
            * max(len(WORLD_SKILL_BUNDLES), 1)
        )
        return {
            "headline": "Global recruitment atlas is live across the brain mesh.",
            "atlas_mode": "full_iso" if pycountry is not None else "fallback_country_pack",
            "metrics": {
                "seeded_atoms": int(atom_count),
                "official_source_packs": int(source_count),
                "country_nodes": int(country_count),
                "subdivision_nodes": int(subdivision_count()),
                "domains": len(WORLD_ATLAS_DOMAINS),
                "role_families": len(WORLD_ROLE_FAMILIES),
                "candidate_axes": len(WORLD_CANDIDATE_AXES),
                "skill_bundles": len(WORLD_SKILL_BUNDLES),
                "possible_thoughts": int(possible_thoughts),
            },
            "domains": WORLD_ATLAS_DOMAINS[:8],
            "regions": WORLD_ATLAS_REGIONS,
            "role_families": WORLD_ROLE_FAMILIES[:8],
            "candidate_axes": WORLD_CANDIDATE_AXES[:10],
            "sources": relevant_sources("law rights population government"),
            "samples": [
                {
                    "title": row.get("title"),
                    "summary": row.get("summary"),
                    "domain": row.get("domain"),
                    "geo_scope": row.get("geo_scope"),
                }
                for row in search_world_atoms("", limit=6)
            ],
            "policy": [
                "Keep geography, candidate-intelligence, and role-family knowledge permanently available.",
                "Treat exact laws, rights, public-service grades, and district rules as live-check data.",
                "Use guided disclosure for candidate data and avoid irrelevant broad dumps.",
            ],
        }

    ensure_tables()
    seed_sources()
    seed_world_atoms()
    broadcast_world_references()

    @app.get("/api/world-brain/status")
    async def get_world_brain_status(request: Request):
        require_session(request)
        return status_payload()

    @app.get("/api/world-brain/query")
    async def query_world_brain(request: Request, q: str = "", limit: int = 8):
        require_session(request)
        size = max(1, min(limit, 20))
        return {
            "query": q,
            "results": search_world_atoms(q, limit=size),
            "sources": relevant_sources(q, limit=4),
            "brief": context_brief(q, limit=min(size, 12)),
        }

    return {
        "status_payload": status_payload,
        "context_brief": context_brief,
    }
