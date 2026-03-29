"""
Intel router – brain knowledge, web search, RSS news, and URL fetch.

Handles /api/intel/* endpoints (master-only):
  - /api/intel/search       — DuckDuckGo web search → stored as brain knowledge
  - /api/intel/news         — RSS news feed ingestion → stored as brain knowledge
  - /api/intel/fetch-url    — Fetch & store arbitrary URL content
  - /api/intel/knowledge/{brain_id} — Retrieve knowledge for a single brain
  - /api/intel/all-knowledge        — Retrieve all stored knowledge
  - /api/intel/mass-learn           — Batch-learn across all key brains
  - /api/intel/sources              — List configured feed sources
"""
import re
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import quote_plus
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class IntelSearchReq(BaseModel):
    query: str
    brain_id: str = "anveshan"


class IntelNewsReq(BaseModel):
    category: str = "tech"
    brain_id: str = "anveshan"


class IntelFetchReq(BaseModel):
    url: str
    brain_id: str = "anveshan"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_intel_router(ctx: Dict[str, Any]) -> APIRouter:
    """Return an APIRouter with all /api/intel/* routes registered."""

    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    emit_carbon = ctx["emit_carbon"]
    news_feeds: Dict[str, List[str]] = ctx["NEWS_FEEDS"]
    log = ctx["log"]

    router = APIRouter()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def require_master(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user or user.get("role") != "master":
            raise HTTPException(status_code=403, detail="Imperial access required")
        return user

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
            r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>'
            r'[\s\S]{0,800}?<a[^>]*class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
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

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @router.post("/api/intel/search")
    async def intel_search(req: IntelSearchReq, request: Request):
        require_master(request)
        results = await ddg_search(req.query)
        stored = []
        for item in results:
            kid = store_brain_knowledge(req.brain_id, "web_search", item["title"], item["url"], item["snippet"], item["snippet"], req.query, 0.72)
            stored.append({**item, "id": kid})
        emit_carbon("intel_search", {"brain_id": req.brain_id, "query": req.query, "count": len(stored)}, "graphene")
        return {"ok": True, "brain_id": req.brain_id, "query": req.query, "stored": len(stored), "results": stored}

    @router.post("/api/intel/news")
    async def intel_news(req: IntelNewsReq, request: Request):
        require_master(request)
        items: List[Dict[str, str]] = []
        for feed in news_feeds.get(req.category, news_feeds["tech"])[:2]:
            items.extend(await fetch_rss_items(feed, limit=4))
        stored = []
        for item in items[:8]:
            kid = store_brain_knowledge(req.brain_id, "news_feed", item["title"], item["url"], item["snippet"], item["snippet"], req.category, 0.75)
            stored.append({**item, "id": kid})
        emit_carbon("intel_news", {"brain_id": req.brain_id, "category": req.category, "count": len(stored)}, "graphene")
        return {"ok": True, "brain_id": req.brain_id, "category": req.category, "stored": len(stored), "results": stored}

    @router.post("/api/intel/fetch-url")
    async def intel_fetch_url(req: IntelFetchReq, request: Request):
        require_master(request)
        content = await fetch_url_text(req.url)
        kid = store_brain_knowledge(req.brain_id, "url_fetch", f"Fetched: {req.url[:80]}", req.url, content, content[:400], "url_fetch", 0.8)
        emit_carbon("url_fetched", {"brain_id": req.brain_id, "url": req.url[:100]}, "nanotube")
        return {"ok": True, "brain_id": req.brain_id, "url": req.url, "id": kid, "content_length": len(content), "preview": content[:400]}

    @router.get("/api/intel/knowledge/{brain_id}")
    async def get_brain_knowledge(brain_id: str, request: Request):
        require_master(request)
        rows = db_all("SELECT * FROM brain_knowledge WHERE brain_id=? ORDER BY learned_at DESC LIMIT 20", (brain_id,)) or []
        return {
            "brain_id": brain_id,
            "brain_name": brain_id.replace("_", " "),
            "knowledge": rows,
            "total_learned": len(rows),
            "learning_score": min(0.99, 0.4 + len(rows) * 0.03),
        }

    @router.get("/api/intel/all-knowledge")
    async def get_all_knowledge(request: Request):
        require_master(request)
        rows = db_all("SELECT * FROM brain_knowledge ORDER BY learned_at DESC LIMIT 50") or []
        return {"knowledge": rows, "total": len(rows)}

    @router.post("/api/intel/mass-learn")
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
                    items: List[Dict[str, str]] = []
                    for feed in news_feeds.get(topic, news_feeds["tech"])[:1]:
                        items.extend(await fetch_rss_items(feed, limit=3))
                    for item in items:
                        store_brain_knowledge(brain_id, "news_feed", item["title"], item["url"], item["snippet"], item["snippet"], topic, 0.74)
                    results[brain_id] = len(items)
                else:
                    web_items = await ddg_search(topic)
                    for item in web_items:
                        store_brain_knowledge(brain_id, "web_search", item["title"], item["url"], item["snippet"], item["snippet"], topic, 0.71)
                    results[brain_id] = len(web_items)
            except Exception as exc:
                log.debug("Mass learn failed for %s: %s", brain_id, exc)
                results[brain_id] = 0
        emit_carbon("mass_learn_complete", {"brains": len(results), "total": sum(results.values())}, "graphene")
        return {"ok": True, "results": results, "total_learned": sum(results.values())}

    @router.get("/api/intel/sources")
    async def intel_get_sources(request: Request):
        require_master(request)
        return {
            "news_feeds": news_feeds,
            "feed_count": sum(len(v) for v in news_feeds.values()),
            "search_engine": "DuckDuckGo HTML",
            "web_scraping": "httpx + regex cleanup",
        }

    return router
