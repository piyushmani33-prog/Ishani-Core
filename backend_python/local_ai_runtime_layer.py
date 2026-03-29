import json
import os
import platform
import re
import shutil
import subprocess
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel

try:
    import chromadb

    CHROMA_AVAILABLE = True
except Exception:
    chromadb = None
    CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import torch

    TORCH_AVAILABLE = True
except Exception:
    torch = None
    TORCH_AVAILABLE = False

try:
    from unstructured.partition.auto import partition

    UNSTRUCTURED_AVAILABLE = True
except Exception:
    partition = None
    UNSTRUCTURED_AVAILABLE = False


class LocalAIConfigRequest(BaseModel):
    enabled: Optional[bool] = None
    runtime_driver: Optional[str] = None
    artifact_format_preference: Optional[str] = None
    embedding_model: Optional[str] = None
    vector_db: Optional[str] = None
    guard_model: Optional[str] = None
    rag_top_k: Optional[int] = None
    allow_gpu_adaptation: Optional[bool] = None


class LocalAIIngestRequest(BaseModel):
    document_ids: List[str] = []
    reindex_all: bool = False
    limit: int = 25


class LocalAIRagQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    prefer_local: bool = True
    target_model: Optional[str] = None
    require_grounding: bool = True


def install_local_ai_runtime_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    db_exec = ctx["db_exec"]
    db_all = ctx["db_all"]
    new_id = ctx["new_id"]
    now_iso = ctx["now_iso"]
    session_user = ctx["session_user"]
    mutate_state = ctx["mutate_state"]
    get_state = ctx["get_state"]
    extract_document_text = ctx["extract_document_text"]
    call_ollama = ctx["call_ollama"]
    extract_ollama_text = ctx["extract_ollama_text"]
    generate_text = ctx["generate_text"]
    sanitize_operator_line = ctx["sanitize_operator_line"]
    sanitize_operator_multiline = ctx["sanitize_operator_multiline"]
    BACKEND_DIR = ctx["BACKEND_DIR"]
    DATA_DIR = ctx["DATA_DIR"]
    OLLAMA_HOST = ctx["OLLAMA_HOST"]
    OLLAMA_MODEL = ctx["OLLAMA_MODEL"]
    AI_NAME = ctx["AI_NAME"]
    CORE_IDENTITY = ctx["CORE_IDENTITY"]
    log = ctx["log"]

    embedder_cache: Dict[str, Any] = {"model_name": "", "device": "", "model": None}
    chroma_cache: Dict[str, Any] = {"client": None, "path": ""}

    def package_version(name: str) -> str:
        try:
            return metadata.version(name)
        except Exception:
            return ""

    def ensure_tables() -> None:
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS local_ai_ingest_runs(
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                document_id TEXT NOT NULL DEFAULT '',
                chunk_count INTEGER NOT NULL DEFAULT 0,
                vector_db TEXT NOT NULL DEFAULT 'chromadb',
                embedding_model TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'indexed',
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        db_exec(
            """
            CREATE TABLE IF NOT EXISTS local_ai_query_runs(
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                query_text TEXT NOT NULL DEFAULT '',
                top_k INTEGER NOT NULL DEFAULT 0,
                runtime_driver TEXT NOT NULL DEFAULT '',
                grounding_count INTEGER NOT NULL DEFAULT 0,
                guard_status TEXT NOT NULL DEFAULT '',
                provider_label TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )

    ensure_tables()

    def require_user(request: Request) -> Dict[str, Any]:
        user = session_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Login required")
        return user

    def runtime_root() -> Path:
        configured = os.getenv("TECHBUZZ_RUNTIME_ROOT", "").strip()
        if configured:
            return Path(configured).expanduser().resolve()
        if os.name == "nt":
            return (Path.home() / "AppData" / "Local" / "TechBuzz").resolve()
        xdg = os.getenv("XDG_DATA_HOME", "").strip()
        if xdg:
            return (Path(xdg).expanduser() / "techbuzz").resolve()
        return (Path.home() / ".local" / "share" / "techbuzz").resolve()

    def model_dirs() -> List[Path]:
        env_dirs = [part.strip() for part in os.getenv("TECHBUZZ_MODEL_DIRS", "").split(os.pathsep) if part.strip()]
        configured = [Path(part).expanduser() for part in env_dirs]
        defaults = [
            runtime_root() / "models",
            DATA_DIR / "models",
            BACKEND_DIR / "models",
        ]
        seen = set()
        resolved: List[Path] = []
        for path in [*configured, *defaults]:
            key = str(path.resolve()) if path.exists() else str(path)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(path)
        return resolved

    def local_ai_settings(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        current = state or get_state()
        settings = current.setdefault("settings", {})
        local_ai = settings.setdefault("local_ai", {})
        local_ai.setdefault("enabled", True)
        local_ai.setdefault("runtime_driver", "ollama")
        local_ai.setdefault("artifact_format_preference", "gguf")
        local_ai.setdefault("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        local_ai.setdefault("vector_db", "chromadb")
        local_ai.setdefault("guard_model", "llama-guard3:latest")
        local_ai.setdefault("rag_top_k", 5)
        local_ai.setdefault("allow_gpu_adaptation", True)
        local_ai.setdefault("last_indexed_at", "")
        return local_ai

    def configure_local_ai(patch: Dict[str, Any]) -> Dict[str, Any]:
        updated: Dict[str, Any] = {}

        def _mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            local_ai = local_ai_settings(state)
            local_ai.update(patch)
            updated.update(local_ai)
            return state

        mutate_state(_mutate)
        return updated

    def gpu_snapshot() -> Dict[str, Any]:
        result = {
            "available": False,
            "backend": "cpu",
            "device_count": 0,
            "devices": [],
            "torch_available": TORCH_AVAILABLE,
        }
        if TORCH_AVAILABLE:
            try:
                if torch.cuda.is_available():
                    result["available"] = True
                    result["backend"] = "cuda"
                    result["device_count"] = torch.cuda.device_count()
                    result["devices"] = [
                        {
                            "name": torch.cuda.get_device_name(index),
                            "index": index,
                        }
                        for index in range(torch.cuda.device_count())
                    ]
                    return result
                if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                    result["available"] = True
                    result["backend"] = "mps"
                    result["device_count"] = 1
                    result["devices"] = [{"name": "Apple Metal", "index": 0}]
                    return result
            except Exception:
                pass
        if shutil.which("nvidia-smi"):
            try:
                completed = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
                names = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
                if names:
                    result["available"] = True
                    result["backend"] = "cuda"
                    result["device_count"] = len(names)
                    result["devices"] = [{"name": name, "index": index} for index, name in enumerate(names)]
            except Exception:
                pass
        return result

    def platform_snapshot() -> Dict[str, Any]:
        root = runtime_root()
        root.mkdir(parents=True, exist_ok=True)
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "runtime_root": str(root),
            "model_dirs": [str(path) for path in model_dirs()],
            "mobile_access": "The backend runs on the host OS. Android and iOS access this stack through the browser/PWA layer rather than native local execution.",
            "cross_platform_note": "Windows and Linux use the same FastAPI core now. Path resolution prefers environment variables and standard user-data directories instead of hardcoded Windows-only storage.",
        }

    def discover_model_artifacts(limit: int = 32) -> Dict[str, List[Dict[str, Any]]]:
        gguf: List[Dict[str, Any]] = []
        exl2: List[Dict[str, Any]] = []
        generic: List[Dict[str, Any]] = []
        for directory in model_dirs():
            if not directory.exists():
                continue
            for path in directory.rglob("*"):
                if len(gguf) + len(exl2) + len(generic) >= limit:
                    break
                lowered = path.name.lower()
                if path.is_file() and path.suffix.lower() == ".gguf":
                    gguf.append(
                        {
                            "name": path.name,
                            "path": str(path),
                            "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
                            "runtime_hint": "llama.cpp / Ollama-compatible GGUF artifact",
                        }
                    )
                elif path.is_dir() and "exl2" in lowered:
                    exl2.append(
                        {
                            "name": path.name,
                            "path": str(path),
                            "runtime_hint": "ExLlamaV2 / EXL2 quantized model directory",
                        }
                    )
                elif path.is_file() and path.suffix.lower() in {".safetensors", ".bin"}:
                    generic.append(
                        {
                            "name": path.name,
                            "path": str(path),
                            "runtime_hint": "Transformer checkpoint or generic weight artifact",
                        }
                    )
            if len(gguf) + len(exl2) + len(generic) >= limit:
                break
        return {"gguf": gguf, "exl2": exl2, "generic": generic}

    def choose_embedding_device() -> str:
        gpu = gpu_snapshot()
        if gpu.get("backend") == "cuda":
            return "cuda"
        return "cpu"

    def get_embedder(model_name: str):
        if not SENTENCE_TRANSFORMERS_AVAILABLE or SentenceTransformer is None:
            raise HTTPException(status_code=503, detail="sentence-transformers is not available")
        device = choose_embedding_device()
        if (
            embedder_cache.get("model") is None
            or embedder_cache.get("model_name") != model_name
            or embedder_cache.get("device") != device
        ):
            embedder_cache["model"] = SentenceTransformer(model_name, device=device)
            embedder_cache["model_name"] = model_name
            embedder_cache["device"] = device
        return embedder_cache["model"]

    def vector_path() -> Path:
        path = runtime_root() / "vector_store" / "chromadb"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def chroma_client():
        if not CHROMA_AVAILABLE or chromadb is None:
            raise HTTPException(status_code=503, detail="ChromaDB is not available")
        path = str(vector_path())
        if chroma_cache.get("client") is None or chroma_cache.get("path") != path:
            chroma_cache["client"] = chromadb.PersistentClient(path=path)
            chroma_cache["path"] = path
        return chroma_cache["client"]

    def collection_name(user_id: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9_]+", "_", user_id or "default").strip("_").lower()
        return f"techbuzz_local_ai_{clean}"[:63]

    def chroma_collection(user_id: str):
        client = chroma_client()
        return client.get_or_create_collection(name=collection_name(user_id), metadata={"source": "techbuzz_local_ai"})

    def document_rows(user_id: str, doc_ids: List[str], limit: int, reindex_all: bool) -> List[Dict[str, Any]]:
        if doc_ids:
            placeholders = ",".join("?" for _ in doc_ids)
            return db_all(
                f"""
                SELECT id, original_name, mime_type, extension, storage_path, summary, extracted_text, created_at
                FROM documents
                WHERE user_id=? AND id IN ({placeholders})
                ORDER BY created_at DESC
                """,
                (user_id, *doc_ids),
            )
        return db_all(
            """
            SELECT id, original_name, mime_type, extension, storage_path, summary, extracted_text, created_at
            FROM documents
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, max(1, min(limit, 100 if reindex_all else 40))),
        )

    def clean_partition_text(raw_text: str) -> str:
        return sanitize_operator_multiline((raw_text or "").replace("\x00", " ")).strip()

    def extract_with_unstructured(path: Path) -> str:
        if not UNSTRUCTURED_AVAILABLE or partition is None:
            return ""
        try:
            elements = partition(filename=str(path))
            text = "\n".join(getattr(element, "text", "") for element in elements if getattr(element, "text", "").strip())
            return clean_partition_text(text)
        except Exception:
            return ""

    def extract_for_rag(row: Dict[str, Any]) -> str:
        path = Path(row.get("storage_path", ""))
        mime_type = row.get("mime_type", "application/octet-stream")
        if path.exists():
            text = extract_with_unstructured(path)
            if text:
                return text
            extracted = extract_document_text(path, mime_type)
            if extracted:
                return clean_partition_text(extracted)
        return clean_partition_text(row.get("extracted_text", "") or row.get("summary", ""))

    def chunk_text(text: str, size: int = 1100, overlap: int = 180) -> List[str]:
        clean = " ".join((text or "").split())
        if not clean:
            return []
        chunks: List[str] = []
        start = 0
        while start < len(clean):
            end = min(len(clean), start + size)
            chunks.append(clean[start:end])
            if end >= len(clean):
                break
            start = max(0, end - overlap)
        return chunks

    def token_set(text: str) -> set[str]:
        return {token.lower() for token in re.findall(r"[a-zA-Z0-9_]{3,}", text or "")}

    def overlap_score(query: str, text: str) -> int:
        return len(token_set(query) & token_set(text))

    def extractive_grounded_answer(query: str, hits: List[Dict[str, Any]]) -> str:
        candidates: List[tuple[int, str]] = []
        for hit in hits:
            for sentence in re.split(r"(?<=[.!?])\s+", hit.get("text", "")):
                clean = sanitize_operator_line(sentence)
                if len(clean) < 24:
                    continue
                score = overlap_score(query, clean)
                if hit.get("document_name"):
                    score += 1
                candidates.append((score, clean))
        candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        best = [text for score, text in candidates if score > 0][:3]
        if not best:
            fallback = hits[0].get("text", "")[:360] if hits else "The indexed documents do not contain enough grounded detail yet."
            best = [sanitize_operator_multiline(fallback)]
        return "Based on the indexed local documents: " + " ".join(best)

    def embed_texts(texts: List[str], model_name: str) -> List[List[float]]:
        model = get_embedder(model_name)
        vectors = model.encode(texts, normalize_embeddings=True)
        if hasattr(vectors, "tolist"):
            return vectors.tolist()
        return [list(item) for item in vectors]

    async def guard_text(text: str, *, direction: str) -> Dict[str, Any]:
        local_ai = local_ai_settings()
        model_name = local_ai.get("guard_model", "llama-guard3:latest")
        cleaned = sanitize_operator_multiline(text or "")
        if not cleaned:
            return {"allowed": True, "mode": "empty", "label": "safe", "reason": "No content supplied."}
        try:
            result = await call_ollama(
                prompt=(
                    f"Classify this {direction} text as SAFE or BLOCK. "
                    f"Return one line: SAFE or BLOCK, then a short reason.\n\n{cleaned[:2500]}"
                ),
                system="You are a strict local safety classifier for enterprise AI. Block toxic, credential-seeking, or high-risk unsafe content.",
                model=model_name,
                max_tokens=80,
                timeout_seconds=15.0,
            )
            text_reply = (extract_ollama_text(result) or "").strip()
            lowered = text_reply.lower()
            allowed = "block" not in lowered or "safe" in lowered.splitlines()[0]
            return {
                "allowed": allowed,
                "mode": "llama_guard_local",
                "label": "safe" if allowed else "blocked",
                "reason": text_reply[:280],
            }
        except Exception:
            risky = any(
                token in cleaned.lower()
                for token in ("password", "credit card", "cvv", "ssn", "aadhaar", "violent attack", "bomb recipe")
            )
            return {
                "allowed": not risky,
                "mode": "rule_fallback",
                "label": "blocked" if risky else "safe",
                "reason": "Fallback lexical guardrail applied." if risky else "No lexical guard hit.",
            }

    def vector_stats(user_id: str) -> Dict[str, Any]:
        if not CHROMA_AVAILABLE:
            return {"available": False, "path": str(vector_path()), "collection": collection_name(user_id), "count": 0}
        collection = chroma_collection(user_id)
        count = int(collection.count() or 0)
        return {
            "available": True,
            "path": str(vector_path()),
            "collection": collection_name(user_id),
            "count": count,
        }

    def status_payload(viewer: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        local_ai = local_ai_settings()
        models = discover_model_artifacts()
        user_id = viewer.get("id", "") if viewer else ""
        vector = vector_stats(user_id) if user_id else {"available": CHROMA_AVAILABLE, "path": str(vector_path()), "collection": "", "count": 0}
        return {
            "platform": platform_snapshot(),
            "gpu": gpu_snapshot(),
            "local_ai": dict(local_ai),
            "runtimes": {
                "driver": local_ai.get("runtime_driver", "ollama"),
                "ollama_host": OLLAMA_HOST,
                "ollama_model": OLLAMA_MODEL,
                "llama_cpp_url": os.getenv("TECHBUZZ_LLAMA_CPP_URL", "").strip(),
                "exl2_url": os.getenv("TECHBUZZ_EXL2_URL", "").strip(),
                "gguf": models["gguf"],
                "exl2": models["exl2"],
                "generic": models["generic"][:8],
                "adoption": {
                    "current_mode": "hosted_backend_with_mobile_web_access",
                    "preferred_quant": local_ai.get("artifact_format_preference", "gguf"),
                    "gpu_adaptation": bool(local_ai.get("allow_gpu_adaptation", True)),
                },
            },
            "embeddings": {
                "available": SENTENCE_TRANSFORMERS_AVAILABLE,
                "package": package_version("sentence-transformers"),
                "model": local_ai.get("embedding_model", ""),
                "device": choose_embedding_device() if SENTENCE_TRANSFORMERS_AVAILABLE else "unavailable",
            },
            "vector_db": {
                "available": CHROMA_AVAILABLE,
                "package": package_version("chromadb"),
                "driver": local_ai.get("vector_db", "chromadb"),
                **vector,
            },
            "document_ingestion": {
                "unstructured_available": UNSTRUCTURED_AVAILABLE,
                "package": package_version("unstructured"),
                "mode": "unstructured_first_then_builtin_fallback",
                "last_indexed_at": local_ai.get("last_indexed_at", ""),
            },
            "guardrails": {
                "guard_model": local_ai.get("guard_model", ""),
                "mode": "llama_guard_if_available_else_rule_fallback",
            },
            "notes": {
                "linux": "Use START.sh on Linux or macOS. The runtime root follows XDG or standard user-data directories.",
                "mobile": "Android and iOS connect through the browser/PWA layer while the backend runs on a host machine or container.",
                "grounding": "RAG answers use local vector hits first, then the local Llama lane for grounded response generation.",
            },
        }

    async def local_runtime_generate(*, prompt: str, system: str, target_model: str) -> Dict[str, Any]:
        local_ai = local_ai_settings()
        runtime_driver = local_ai.get("runtime_driver", "ollama")
        if runtime_driver == "ollama":
            result = await call_ollama(
                prompt=prompt,
                system=system,
                model=target_model,
                max_tokens=700,
                timeout_seconds=45.0,
            )
            return {"text": extract_ollama_text(result), "provider": f"ollama/{target_model}"}

        if runtime_driver == "llama_cpp_server":
            base_url = os.getenv("TECHBUZZ_LLAMA_CPP_URL", "").strip()
        else:
            base_url = os.getenv("TECHBUZZ_EXL2_URL", "").strip()
        if not base_url:
            raise HTTPException(status_code=503, detail=f"{runtime_driver} is selected but no local server URL is configured")

        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 700,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.post(f"{base_url.rstrip('/')}/v1/chat/completions", json=payload)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"{runtime_driver} local server error: {response.text[:280]}")
        body = response.json()
        text = ""
        if isinstance(body.get("choices"), list) and body["choices"]:
            message = body["choices"][0].get("message", {}) or {}
            text = message.get("content", "") or ""
        return {"text": text.strip(), "provider": f"{runtime_driver}/{target_model}"}

    @app.get("/api/local-ai/status")
    async def local_ai_status(request: Request):
        user = require_user(request)
        return status_payload(user)

    @app.post("/api/local-ai/configure")
    async def local_ai_configure(req: LocalAIConfigRequest, request: Request):
        require_user(request)
        patch: Dict[str, Any] = {}
        if req.enabled is not None:
            patch["enabled"] = bool(req.enabled)
        if req.runtime_driver is not None:
            candidate = (req.runtime_driver or "").strip().lower() or "ollama"
            if candidate not in {"ollama", "llama_cpp_server", "exl2_server"}:
                candidate = "ollama"
            patch["runtime_driver"] = candidate
        if req.artifact_format_preference is not None:
            candidate = (req.artifact_format_preference or "").strip().lower() or "gguf"
            if candidate not in {"gguf", "exl2"}:
                candidate = "gguf"
            patch["artifact_format_preference"] = candidate
        if req.embedding_model is not None:
            patch["embedding_model"] = (req.embedding_model or "").strip() or "sentence-transformers/all-MiniLM-L6-v2"
        if req.vector_db is not None:
            patch["vector_db"] = "chromadb"
        if req.guard_model is not None:
            patch["guard_model"] = (req.guard_model or "").strip() or "llama-guard3:latest"
        if req.rag_top_k is not None:
            patch["rag_top_k"] = max(1, min(int(req.rag_top_k), 12))
        if req.allow_gpu_adaptation is not None:
            patch["allow_gpu_adaptation"] = bool(req.allow_gpu_adaptation)
        updated = configure_local_ai(patch)
        return {"message": "Local AI runtime updated.", "local_ai": updated}

    @app.post("/api/local-ai/ingest")
    async def local_ai_ingest(req: LocalAIIngestRequest, request: Request):
        user = require_user(request)
        local_ai = local_ai_settings()
        rows = document_rows(user["id"], req.document_ids, req.limit, req.reindex_all)
        if not rows:
            return {"message": "No documents available for indexing.", "indexed_documents": 0, "indexed_chunks": 0}
        if not CHROMA_AVAILABLE:
            raise HTTPException(status_code=503, detail="ChromaDB is not installed")
        collection = chroma_collection(user["id"])
        indexed_documents = 0
        indexed_chunks = 0
        details: List[Dict[str, Any]] = []
        for row in rows:
            text = extract_for_rag(row)
            chunks = chunk_text(text)
            if not chunks:
                continue
            embeddings = embed_texts(chunks, local_ai.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"))
            try:
                existing = collection.get(where={"document_id": row["id"]}, include=[])
                ids_to_delete = existing.get("ids", []) if isinstance(existing, dict) else []
                if ids_to_delete:
                    collection.delete(ids=ids_to_delete)
            except Exception:
                pass
            ids = [f"{row['id']}::{index}" for index in range(len(chunks))]
            metadatas = [
                {
                    "document_id": row["id"],
                    "document_name": row.get("original_name", ""),
                    "chunk_index": index,
                    "source": "documents",
                }
                for index in range(len(chunks))
            ]
            collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
            indexed_documents += 1
            indexed_chunks += len(chunks)
            details.append({"document_id": row["id"], "name": row.get("original_name", ""), "chunks": len(chunks)})
            db_exec(
                """
                INSERT INTO local_ai_ingest_runs(id,user_id,document_id,chunk_count,vector_db,embedding_model,status,detail,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    new_id("ing"),
                    user["id"],
                    row["id"],
                    len(chunks),
                    local_ai.get("vector_db", "chromadb"),
                    local_ai.get("embedding_model", ""),
                    "indexed",
                    row.get("original_name", ""),
                    now_iso(),
                ),
            )
        configure_local_ai({"last_indexed_at": now_iso()})
        return {
            "message": f"Indexed {indexed_documents} document(s) into the local vector memory.",
            "indexed_documents": indexed_documents,
            "indexed_chunks": indexed_chunks,
            "vector_db": vector_stats(user["id"]),
            "details": details,
        }

    @app.post("/api/local-ai/rag/query")
    async def local_ai_rag_query(req: LocalAIRagQueryRequest, request: Request):
        user = require_user(request)
        local_ai = local_ai_settings()
        if not local_ai.get("enabled", True):
            raise HTTPException(status_code=400, detail="Local AI runtime is disabled")
        query = sanitize_operator_multiline(req.query or "")
        guard_input = await guard_text(query, direction="input")
        if not guard_input.get("allowed", True):
            raise HTTPException(status_code=400, detail=f"Guardrail blocked the request: {guard_input.get('reason', '')}")
        if not CHROMA_AVAILABLE:
            raise HTTPException(status_code=503, detail="ChromaDB is not installed")
        collection = chroma_collection(user["id"])
        if int(collection.count() or 0) <= 0:
            raise HTTPException(status_code=400, detail="No indexed local documents found. Run local ingestion first.")

        query_vector = embed_texts([query], local_ai.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"))[0]
        top_k = max(1, min(req.top_k or local_ai.get("rag_top_k", 5), 10))
        result = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        hits = []
        for index, document in enumerate(documents):
            metadata_row = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None
            hits.append(
                {
                    "document_id": metadata_row.get("document_id", ""),
                    "document_name": metadata_row.get("document_name", ""),
                    "chunk_index": metadata_row.get("chunk_index", index),
                    "distance": distance,
                    "text": document[:1000],
                }
            )
        context = "\n\n".join(
            f"[{hit['document_name']}#{hit['chunk_index']}]\n{hit['text']}"
            for hit in hits
        )
        system = sanitize_operator_multiline(
            f"""
You are {AI_NAME}, the grounded local retrieval intelligence of {CORE_IDENTITY}.
Answer only from the supplied local context.
If the context is incomplete, say exactly what is missing.
Be concise and practical.
"""
        ).strip()
        prompt = sanitize_operator_multiline(
            f"""
User question:
{query}

Retrieved local context:
{context}

Instructions:
- Ground every answer in the retrieved context.
- If you infer anything, label it clearly.
- Do not invent facts that are not present.
"""
        ).strip()
        target_model = (req.target_model or "").strip() or OLLAMA_MODEL
        try:
            if req.prefer_local:
                llm_result = await local_runtime_generate(prompt=prompt, system=system, target_model=target_model)
                answer = sanitize_operator_multiline(llm_result.get("text", ""))
                provider_label = llm_result.get("provider", f"ollama/{target_model}")
            else:
                generated = await generate_text(prompt, system=system, max_tokens=700, use_web_search=False, source="manual", workspace="local_rag")
                answer = sanitize_operator_multiline(generated.get("text", ""))
                provider_label = generated.get("provider", "built-in")
        except Exception:
            generated = await generate_text(prompt, system=system, max_tokens=700, use_web_search=False, source="manual", workspace="local_rag")
            answer = sanitize_operator_multiline(generated.get("text", ""))
            provider_label = generated.get("provider", "built-in")

        guard_output = await guard_text(answer, direction="output")
        grounded_fallback = extractive_grounded_answer(query, hits)
        context_reference_score = max((overlap_score(hit.get("text", ""), answer) for hit in hits), default=0)
        generic_drift = any(
            phrase in answer.lower()
            for phrase in (
                "i'm leazy jinn",
                "what's the priority task",
                "what can i help",
                "what's your request",
                "senior recruiter hire",
            )
        )
        grounded_enough = context_reference_score >= 4 and not generic_drift
        final_answer = answer if guard_output.get("allowed", True) else "Guardrail blocked the generated answer. Refine the question or reduce sensitive content."
        if req.require_grounding and (not grounded_enough or generic_drift):
            final_answer = grounded_fallback
        db_exec(
            """
            INSERT INTO local_ai_query_runs(id,user_id,query_text,top_k,runtime_driver,grounding_count,guard_status,provider_label,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                new_id("rag"),
                user["id"],
                query[:500],
                top_k,
                local_ai.get("runtime_driver", "ollama"),
                len(hits),
                guard_output.get("label", "safe"),
                provider_label,
                now_iso(),
            ),
        )
        return {
            "answer": final_answer,
            "provider": provider_label,
            "grounding_hits": hits,
            "guardrails": {"input": guard_input, "output": guard_output},
            "runtime": {
                "driver": local_ai.get("runtime_driver", "ollama"),
                "artifact_preference": local_ai.get("artifact_format_preference", "gguf"),
                "target_model": target_model,
            },
            "vector_db": vector_stats(user["id"]),
        }

    return {
        "status": "loaded",
        "status_payload": status_payload,
    }
