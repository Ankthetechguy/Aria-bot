# Aria — Wellness Voice & Chat Bot

A fully local Python-powered AI bot with:
- 💬 Streaming chat (like ChatGPT)
- 🎙️ Voice mode: speak → Whisper STT → Gemini Flash → edge-tts audio reply
- 🎨 Premium dark UI with audio playback controls

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note on Whisper:** First run will auto-download the `base` model (~140MB).
> For faster/lighter: change `WHISPER_MODEL = "tiny"` in main.py

### 2. Get your Gemini API key (free)
- Go to: https://aistudio.google.com/app/apikey
- Copy your key

### 3. Set your API key
**Option A — Environment variable (recommended):**
```bash
# Windows PowerShell
$env:GEMINI_API_KEY = "your_key_here"

# Windows CMD
set GEMINI_API_KEY=your_key_here
```

**Option B — Edit main.py directly:**
```python
GEMINI_API_KEY = "your_key_here"   # line 10
```

### 4. Run
```bash
python main.py
```

### 5. Open browser
Go to: **http://localhost:8000**

---

## Customization

### Change the bot's knowledge (system prompt)
Edit the `SYSTEM_PROMPT` variable in `main.py` — add your real:
- Service details
- Pricing in INR
- Trainer name
- Booking link

### Change TTS voice
Edit `TTS_VOICE` in `main.py`. Options:
- `en-US-JennyNeural` — warm female (default)
- `en-US-GuyNeural` — male
- `en-IN-NeerjaNeural` — Indian female accent
- `en-IN-PrabhatNeural` — Indian male accent

Run `edge-tts --list-voices` to see all voices.

### Whisper model sizes
| Model | Size  | Speed   | Accuracy |
|-------|-------|---------|----------|
| tiny  | 75MB  | Fastest | Good     |
| base  | 140MB | Fast    | Better   |
| small | 460MB | Slower  | Best     |

---

## Architecture

```
Browser (index.html)
  │
  ├── POST /transcribe     → Whisper STT → transcript text
  ├── POST /chat/stream    → Gemini Flash streaming → SSE deltas
  └── POST /tts            → edge-tts → MP3 audio bytes
```

---

## Files
```
aria-wellness-bot/
├── main.py          ← FastAPI backend (all logic)
├── index.html       ← Frontend UI (served by FastAPI)
├── requirements.txt ← Python dependencies
└── README.md
```