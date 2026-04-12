import os
import asyncio
import tempfile
import json
import re
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import edge_tts
import google.generativeai as genai
from faster_whisper import WhisperModel

# ── CONFIG ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
TTS_VOICE      = "en-US-JennyNeural"   # edge-tts voice  (warm, natural)
WHISPER_MODEL  = "base"                # tiny / base / small  (base = best balance)
MAX_CONTEXT_MESSAGES = 16               # keep recent context for snappy, coherent replies

genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are Aria, a warm and knowledgeable wellness guide for a fitness and wellness company specializing in Kumbhak therapy - an ancient breathwork practice involving conscious breath retention (pranayama).

You help potential customers understand:
- What Kumbhak therapy is and its deep benefits: stress relief, improved lung capacity, mental clarity, nervous system regulation, improved sleep
- Services offered: 1-on-1 personalized sessions, group breathwork classes, 4-week online programs, corporate wellness packages
- Pricing: Discovery call is FREE. 1-on-1 sessions start at ₹1500/session. Monthly programs at ₹5000/month. Corporate packages custom-quoted.
- How to book: Visit our website or ask Aria to connect you with a trainer directly

Personality: Warm, calm, encouraging — like a trusted wellness friend, not a salesperson.
Keep replies concise and natural.

Conversation style rules:
- Sound human and conversational, not scripted.
- Start by acknowledging the user's latest message naturally.
- Answer the exact question first, then add one useful detail.
- Ask one short follow-up question when it helps continue the conversation.
- Do not dump every service or price unless the user asks.
- Use short paragraphs, no markdown, no bullet points in replies.
"""


def _normalize_role(role: str) -> str:
    if role in {"assistant", "bot", "model"}:
        return "model"
    return "user"


def _build_history(messages: list[dict]) -> list[dict]:
    recent = messages[-MAX_CONTEXT_MESSAGES:]
    history = []
    for m in recent[:-1]:
        history.append(
            {
                "role": _normalize_role(m.get("role", "user")),
                "parts": [m.get("content", "")],
            }
        )
    return history

# Load faster-whisper model once at startup (no ffmpeg needed!)
print("⏳ Loading Whisper model...")
whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
print("✅ Whisper ready!")

# ── APP ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="Aria Wellness Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROUTES ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Receive audio blob from browser → return transcript text."""
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        segments, _ = whisper_model.transcribe(tmp_path, language="en", beam_size=5)
        transcript = " ".join(seg.text for seg in segments).strip()
        return JSONResponse({"transcript": transcript})
    finally:
        os.unlink(tmp_path)


@app.post("/chat/stream")
async def chat_stream(payload: dict):
    """
    Streaming text chat.
    payload: { "messages": [...], "voice_mode": false }
    Streams back Server-Sent Events with delta text.
    """
    messages = payload.get("messages", [])
    voice_mode = payload.get("voice_mode", False)

    if not messages:
        return JSONResponse({"error": "No messages provided"}, status_code=400)

    system = SYSTEM_PROMPT
    if voice_mode:
        system += "\n\nVOICE MODE: Keep it flowing and spoken. Use 1-3 short sentences and conversational phrasing."

    history = _build_history(messages)

    user_text = messages[-1]["content"] if messages else ""

    def generate():
        request_model = genai.GenerativeModel(
            MODEL_NAME,
            system_instruction=system,
        )
        chat = request_model.start_chat(history=history)
        response = chat.send_message(
            user_text,
            stream=True,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=220 if voice_mode else 420,
                temperature=0.85 if voice_mode else 0.78,
                top_p=0.92,
            )
        )
        for chunk in response:
            if chunk.text:
                data = json.dumps({"delta": chunk.text})
                yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/tts")
async def text_to_speech(payload: dict):
    """Convert text to speech using edge-tts → return mp3 bytes."""
    text = payload.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)

    # Clean text for TTS (remove markdown symbols)
    text = re.sub(r"[*_`#]", "", text)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(tmp_path)

    def iter_file():
        with open(tmp_path, "rb") as f:
            yield from f
        os.unlink(tmp_path)

    return StreamingResponse(iter_file(), media_type="audio/mpeg")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)