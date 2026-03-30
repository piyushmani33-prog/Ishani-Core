from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    from silero_vad import load_silero_vad
except Exception:
    load_silero_vad = None

try:
    from melo.api import TTS as MeloTTS
except Exception:
    MeloTTS = None


def install_voice_runtime_layer(app, ctx: Dict[str, Any]) -> Dict[str, Any]:
    session_user = ctx["session_user"]
    mutate_state = ctx["mutate_state"]
    get_state = ctx["get_state"]
    execute_voice_command = ctx["execute_voice_command"]
    now_iso = ctx["now_iso"]
    BACKEND_DIR = Path(ctx["BACKEND_DIR"])
    DATA_DIR = Path(ctx["DATA_DIR"])
    log = ctx["log"]

    runtime_dir = DATA_DIR / "voice_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    whisper_cache: Dict[str, Any] = {}

    def default_config() -> Dict[str, Any]:
        return {
            "stt_engine": "faster_whisper",
            "whisper_model": os.getenv("TECHBUZZ_WHISPER_MODEL", "base"),
            "vad_engine": "silero_vad",
            "use_vad": True,
            "tts_engine": "pyttsx3_local",
            "streaming_enabled": True,
            "response_style": "concise_enterprise",
            "language": "en-IN",
            "playback_mode": "local_file",
            "last_transcript_at": "",
            "last_response_at": "",
        }

    def current_config() -> Dict[str, Any]:
        state = get_state()
        settings = state.setdefault("settings", {})
        existing = settings.get("voice_runtime") or {}
        merged = {**default_config(), **existing}
        settings["voice_runtime"] = merged
        return merged

    def gpu_status() -> Dict[str, Any]:
        summary = {"detected": False, "label": "CPU"}
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                first = result.stdout.strip().splitlines()[0].strip()
                summary = {"detected": True, "label": first}
        except Exception:
            pass
        return summary

    def status_payload(viewer: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        config = current_config()
        stt_available = WhisperModel is not None
        vad_available = load_silero_vad is not None
        pyttsx3_available = pyttsx3 is not None
        melo_available = MeloTTS is not None
        preferred_tts = config.get("tts_engine", "pyttsx3_local")
        if preferred_tts == "melo_local" and not melo_available and pyttsx3_available:
            preferred_tts = "pyttsx3_local"
        elif preferred_tts == "melo_local" and not melo_available:
            preferred_tts = "browser_fallback"
        elif preferred_tts == "pyttsx3_local" and not pyttsx3_available:
            preferred_tts = "browser_fallback"
        headline_parts = []
        headline_parts.append("Whisper ready" if stt_available else "Whisper not installed")
        headline_parts.append("Silero VAD ready" if vad_available else "Silero VAD optional")
        if preferred_tts == "melo_local":
            headline_parts.append("MeloTTS ready")
        elif preferred_tts == "pyttsx3_local":
            headline_parts.append("Local TTS ready")
        else:
            headline_parts.append("Browser TTS fallback")
        tts_ok = pyttsx3_available or melo_available
        browser_fallback_active = not tts_ok
        # ready_for_user: user can interact via voice if STT is present OR browser fallback covers TTS
        ready_for_user = stt_available or browser_fallback_active
        # ready_for_automation: requires both STT and local TTS to avoid human-in-the-loop
        ready_for_automation = stt_available and tts_ok
        return {
            "enabled": True,
            "stt_engine": config.get("stt_engine", "faster_whisper"),
            "whisper_model": config.get("whisper_model", "base"),
            "stt_available": stt_available,
            "vad_engine": config.get("vad_engine", "silero_vad"),
            "vad_available": vad_available,
            "use_vad": bool(config.get("use_vad", True)),
            "tts_engine": preferred_tts,
            "tts_available": tts_ok,
            "pyttsx3_available": pyttsx3_available,
            "melo_available": melo_available,
            "browser_tts_fallback_active": browser_fallback_active,
            "streaming_enabled": bool(config.get("streaming_enabled", True)),
            "language": config.get("language", "en-IN"),
            "response_style": config.get("response_style", "concise_enterprise"),
            "gpu": gpu_status(),
            "headline": " | ".join(headline_parts),
            "degraded": not stt_available or not tts_ok,
            "ready_for_user": ready_for_user,
            "ready_for_automation": ready_for_automation,
            "notes": [
                "The local voice loop is capture -> transcribe -> think -> synthesize.",
                "Whisper handles speech-to-text, VAD trims silence, and the main brain produces concise replies.",
                "If no local TTS engine is available, the existing browser voice remains the fallback lane.",
            ],
        }

    def persist_config(patch: Dict[str, Any]) -> Dict[str, Any]:
        def _mutate(state: Dict[str, Any]) -> Dict[str, Any]:
            settings = state.setdefault("settings", {})
            existing = settings.get("voice_runtime") or {}
            merged = {**default_config(), **existing}
            for key, value in patch.items():
                if value is not None:
                    merged[key] = value
            settings["voice_runtime"] = merged
            return merged

        return mutate_state(_mutate)

    def get_whisper_model(config: Dict[str, Any]):
        if WhisperModel is None:
            return None
        model_name = str(config.get("whisper_model", "base") or "base").strip()
        cached = whisper_cache.get(model_name)
        if cached is not None:
            return cached
        gpu = gpu_status()
        device = "cuda" if gpu.get("detected") else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        whisper_cache[model_name] = model
        return model

    def save_upload_to_temp(upload: UploadFile) -> Path:
        suffix = Path(upload.filename or "clip.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=runtime_dir) as tmp:
            upload.file.seek(0)
            tmp.write(upload.file.read())
            return Path(tmp.name)

    def transcribe_audio(audio_path: Path, config: Dict[str, Any], language_hint: str = "") -> Dict[str, Any]:
        model = get_whisper_model(config)
        if model is None:
            raise HTTPException(status_code=503, detail="Faster-Whisper is not installed yet.")
        lang = (language_hint or config.get("language") or "en").strip().lower()
        if "-" in lang:
            lang = lang.split("-", 1)[0]
        segments, info = model.transcribe(
            str(audio_path),
            vad_filter=bool(config.get("use_vad", True)),
            language=lang or None,
            beam_size=1,
            best_of=1,
            condition_on_previous_text=False,
            word_timestamps=False,
        )
        text_segments = []
        for segment in segments:
            snippet = str(getattr(segment, "text", "") or "").strip()
            if snippet:
                text_segments.append(snippet)
        transcript = re.sub(r"\s+", " ", " ".join(text_segments)).strip()
        return {
            "text": transcript,
            "language": getattr(info, "language", lang or "unknown"),
            "duration": float(getattr(info, "duration", 0.0) or 0.0),
            "vad_used": bool(config.get("use_vad", True)),
        }

    def synthesize_text(text: str, config: Dict[str, Any]) -> Dict[str, Any]:
        safe_text = (text or "").strip()
        if not safe_text:
            return {"ok": False, "engine": config.get("tts_engine", "browser_fallback"), "reason": "No text to synthesize."}

        preferred = str(config.get("tts_engine", "pyttsx3_local") or "pyttsx3_local").strip()
        if preferred == "melo_local" and MeloTTS is not None:
            return {
                "ok": False,
                "engine": "melo_local",
                "reason": "MeloTTS is detected but direct file synthesis is not wired in this build yet. Browser playback will be used.",
            }

        if pyttsx3 is None:
            return {
                "ok": False,
                "engine": "browser_fallback",
                "reason": "Local TTS engine is not installed. Browser speech remains the fallback.",
            }

        audio_name = f"{now_iso().replace(':', '').replace('-', '').replace('.', '')}.wav"
        audio_path = runtime_dir / audio_name
        try:
            engine = pyttsx3.init()
            rate = max(120, min(230, int(float(config.get("rate", 0.94) or 0.94) * 190)))
            engine.setProperty("rate", rate)
            engine.save_to_file(safe_text, str(audio_path))
            engine.runAndWait()
            if not audio_path.exists():
                raise RuntimeError("Audio file was not created.")
            return {
                "ok": True,
                "engine": "pyttsx3_local",
                "audio_url": f"/api/voice/runtime/audio/{audio_name}",
                "path": str(audio_path),
            }
        except Exception as exc:
            log.warning("Local TTS synthesis fallback: %s", exc)
            return {
                "ok": False,
                "engine": "browser_fallback",
                "reason": f"Local synthesis failed: {exc}",
            }

    @app.get("/api/voice/runtime/status")
    async def voice_runtime_status(request: Request):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required before opening the local voice runtime.")
        return status_payload(viewer)

    @app.post("/api/voice/runtime/configure")
    async def voice_runtime_configure(request: Request):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required before updating the local voice runtime.")
        body = await request.json()
        allowed = {
            "stt_engine",
            "whisper_model",
            "vad_engine",
            "use_vad",
            "tts_engine",
            "streaming_enabled",
            "response_style",
            "language",
            "rate",
            "pitch",
        }
        patch = {key: body.get(key) for key in allowed if key in body}
        persist_config(patch)
        return {
            "message": "Local voice runtime updated.",
            "voice_runtime": status_payload(viewer),
        }

    @app.post("/api/voice/runtime/transcribe")
    async def voice_runtime_transcribe(
        request: Request,
        file: UploadFile = File(...),
        language: str = Form(""),
    ):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required before transcribing audio.")
        config = current_config()
        temp_path = save_upload_to_temp(file)
        try:
            transcript = transcribe_audio(temp_path, config, language)
            persist_config({"last_transcript_at": now_iso(), "language": language or config.get("language", "en-IN")})
            return {
                "message": "Audio transcribed locally.",
                "transcript": transcript["text"],
                "meta": transcript,
                "voice_runtime": status_payload(viewer),
            }
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

    @app.post("/api/voice/runtime/respond")
    async def voice_runtime_respond(
        request: Request,
        file: UploadFile = File(...),
        mode: str = Form("direct"),
        language: str = Form(""),
        synthesize: str = Form("true"),
    ):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required before running the local voice loop.")
        config = current_config()
        temp_path = save_upload_to_temp(file)
        try:
            transcript = transcribe_audio(temp_path, config, language)
            voice_reply = await execute_voice_command(transcript["text"], mode)
            tts = synthesize_text(voice_reply.get("response", ""), {**config, **(get_state().get("voice") or {})}) if str(synthesize).lower() != "false" else {"ok": False, "engine": "disabled", "reason": "Synthesis skipped by request."}
            persist_config({"last_transcript_at": now_iso(), "last_response_at": now_iso(), "language": language or config.get("language", "en-IN")})
            return {
                "message": "Local voice loop complete.",
                "transcript": transcript["text"],
                "transcript_meta": transcript,
                "wake": voice_reply,
                "tts": tts,
                "voice_runtime": status_payload(viewer),
            }
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass

    @app.post("/api/voice/runtime/tts")
    async def voice_runtime_tts(request: Request):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required before generating local voice playback.")
        body = await request.json()
        text = str(body.get("text") or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required.")
        config = {**current_config(), **(get_state().get("voice") or {})}
        tts = synthesize_text(text, config)
        return {"message": "Voice synthesis attempted.", "tts": tts, "voice_runtime": status_payload(viewer)}

    @app.get("/api/voice/runtime/audio/{audio_name}")
    async def voice_runtime_audio(audio_name: str, request: Request):
        viewer = session_user(request)
        if not viewer:
            raise HTTPException(status_code=401, detail="Login required before fetching generated audio.")
        safe_name = Path(audio_name).name
        target = runtime_dir / safe_name
        if not target.exists() or target.suffix.lower() not in {".wav", ".mp3", ".ogg"}:
            raise HTTPException(status_code=404, detail="Generated audio was not found.")
        return FileResponse(target, media_type="audio/wav", filename=safe_name)

    log.info(
        "Voice runtime layer loaded: Whisper=%s Silero=%s Melo=%s Pyttsx3=%s",
        WhisperModel is not None,
        load_silero_vad is not None,
        MeloTTS is not None,
        pyttsx3 is not None,
    )

    return {
        "status": "loaded",
        "runtime_dir": str(runtime_dir),
        "status_payload": status_payload,
    }
