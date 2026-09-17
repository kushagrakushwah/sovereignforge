# SovereignForge

**Sovereign On-Premise Agentic AI Workbench**

A fully local, zero-external-call agentic AI system that processes documents, executes code, and analyzes images — all running entirely on your machine via [Ollama](https://ollama.ai).

```
User Request
    ↓
FastAPI receives it
    ↓
Task Router classifies it (document / coding / multimodal)
    ↓
ReAct Agent Loop (Think → Act → Observe → Repeat)
    ↓
Tools: OCR | Extract | Draft Word | Code Sandbox | Image VLM
    ↓
Streamed to Next.js UI via WebSocket
    ↓
mitmproxy verifies ZERO external calls
```

---

## Architecture

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Next.js 14 + TypeScript + Tailwind | UI + WebSocket client |
| Backend | FastAPI + uvicorn | REST API + WebSocket server |
| Agent | ReAct loop | Reason → Act → Observe |
| Models | Ollama (local) | LLM inference, no cloud |
| OCR | Tesseract | PDF/image text extraction |
| Sandbox | Docker (no network) | Secure code execution |
| Monitor | mitmproxy | Zero-external-call verification |

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker Desktop** (for code sandbox)
- **Ollama** — [install here](https://ollama.ai)
- **Tesseract OCR** — [Windows installer](https://github.com/UB-Mannheim/tesseract/wiki)

---

## Quick Start

### 1. Pull Ollama Models

```powershell
.\scripts\pull_models.ps1
```

This pulls ~13GB of quantized models:
- `qwen2.5:7b-instruct-q4_K_M` — reasoning/document tasks
- `qwen2.5-coder:7b-instruct-q4_K_M` — coding tasks
- `qwen2.5vl:7b` — vision/multimodal tasks

> **6GB VRAM?** Use `q4_K_M` quantized models (already the default). Ollama auto-swaps models as needed.

### 2. Build the Sandbox

```powershell
docker build -t sovereignforge-sandbox:latest .\sandbox\
```

### 3. Start Everything

```powershell
.\scripts\start_dev.ps1
```

Or manually:

```powershell
# Terminal 1 — Backend
cd backend
..\venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend
npm run dev

# Terminal 3 — Sovereignty Monitor (optional but recommended)
..\venv\Scripts\mitmdump --listen-port 8080 -s ..\sovereignty\mitmproxy_addon.py
```

### 4. Open the UI

→ **http://localhost:3000**

---

## Project Structure

```
sovereignforge/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # All constants and paths
│   ├── schemas.py           # Pydantic models
│   ├── router/
│   │   └── task_router.py   # Classifies: document|coding|multimodal
│   ├── agent/
│   │   ├── loop.py          # ReAct agent loop
│   │   └── prompts.py       # System prompts (iterate here!)
│   ├── tools/
│   │   ├── ocr.py           # Tesseract OCR
│   │   ├── extract.py       # LLM-based structured extraction
│   │   ├── draft_word.py    # python-docx Word generation
│   │   ├── code_sandbox.py  # Docker isolated execution
│   │   └── image_understand.py  # Vision model
│   ├── models/
│   │   └── registry.py      # Single Ollama client
│   └── sovereignty/
│       └── monitor.py       # mitmproxy log reader
├── frontend/
│   ├── app/page.tsx         # Main page (3-column layout)
│   ├── components/          # TaskInput, AgentLog, OutputPanel, NetworkMonitor
│   └── lib/websocket.ts     # WebSocket hooks
├── sandbox/
│   └── Dockerfile           # Isolated Python sandbox
├── sovereignty/
│   └── mitmproxy_addon.py   # Blocks/logs all non-local calls
├── tests/                   # pytest test suite
├── scripts/
│   ├── start_dev.ps1        # Start all services
│   └── pull_models.ps1      # Pull Ollama models
└── docker-compose.yml       # Full stack orchestration
```

---

## The Three Pipelines

### Pipeline A — Document
```
User uploads PDF/DOCX → OCR (Tesseract) → Extract (LLM) → Draft Word (.docx)
```
> "Read this inspection report, extract key findings and risks, and draft an approval note"

### Pipeline B — Coding
```
User describes code task → Agent generates code → Sandbox executes (Docker) → Verify output
```
> "Write a Python function that detects duplicate rows in a CSV file"

### Pipeline C — Multimodal
```
User uploads image → Vision LLM analyzes → Returns text + description
```
> "What is shown in this image? Extract all text and identify all components"

---

## Running Tests

```powershell
# From sovereignforge/ root
.\venv\Scripts\python -m pytest tests/ -v

# Run specific test file
.\venv\Scripts\python -m pytest tests/test_router.py -v

# Run with output (print statements visible)
.\venv\Scripts\python -m pytest tests/ -v -s
```

### Test Coverage
| Test File | What it tests |
|-----------|--------------|
| `test_router.py` | Task classification logic (no LLM) |
| `test_tools.py` | OCR, extract parsing, draft_word, sandbox |
| `test_agent.py` | Agent loop events, tool dispatch (mocked LLM) |
| `test_pipelines.py` | End-to-end pipelines A, B, C (mocked LLM) |

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health + model availability |
| `/upload` | POST | Upload file, get server path |
| `/download/{filename}` | GET | Download generated .docx |
| `/api/classify` | GET | Classify task without running agent |
| `/ws/agent` | WebSocket | Stream agent events |
| `/ws/network` | WebSocket | Real-time network monitor |
| `/docs` | GET | Swagger UI |

---

## Sovereignty Guarantee

Every outbound HTTP call passes through mitmproxy. The addon in `sovereignty/mitmproxy_addon.py`:
1. Logs every request (host, method, URL, timestamp)
2. **Blocks** any call to a non-localhost host with a 403
3. Streams the log to the UI via `/ws/network`

In a correctly configured deployment, the network monitor should always show:
- `sovereign: true`
- `external_blocked: 0`
- Only `localhost:8000` and `localhost:11434` (Ollama) traffic

---

## Configuration

Edit `backend/config.py` to change:
- Model names (use different Ollama models)
- Ports
- Sandbox memory/CPU limits
- Agent iteration limit

Or use environment variables:
```
OLLAMA_BASE_URL=http://localhost:11434
MODEL_REASONING=qwen2.5:7b
MODEL_CODING=qwen2.5-coder:7b
MODEL_VISION=qwen2.5vl:7b
OLLAMA_NUM_CTX=8192          # context window sent with every Ollama call
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
SF_ALLOWED_PATHS=D:\SOPs     # extra dirs agent tools may read (os.pathsep-separated)
```

By default agent tools may only touch files under `<tempdir>/sovereignforge`
(uploads, outputs, knowledge base). Use `SF_ALLOWED_PATHS` to let the agent
ingest an existing document library.

---

## Demo Script

```
1. Open http://localhost:3000
   → Point to bottom bar: "SOVEREIGN ● 0 external calls"

2. PIPELINE A — Document
   → Upload inspection_report.pdf
   → Type: "Extract findings and risks, draft an approval note"
   → Watch: OCR → Extract → Draft Word in the agent log
   → Output panel: click "Download" → .docx opens

3. PIPELINE B — Coding
   → Type: "Write a Python function to detect duplicate CSV rows"
   → Watch: agent generates code → runs in Docker sandbox → shows output

4. PIPELINE C — Multimodal
   → Upload engineering_diagram.png
   → Type: "What is in this image? Extract all text"
   → Watch: VLM analysis streams in

5. SOVEREIGNTY PROOF
   → Show network monitor → every entry is localhost only
   → "This is not a claim. This is a live proof."
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Model takes 60+ seconds | Set `LLM_TIMEOUT_SECONDS=180` in config.py |
| VRAM OOM | Already using q4_K_M quants; ensure only one model loads at a time |
| Sandbox fails | Run `docker build -t sovereignforge-sandbox:latest ./sandbox/` |
| OCR gives garbled text | Increase `OCR_DPI = 300` in config.py |
| WebSocket disconnects | Auto-reconnects after 3 seconds — check backend is running |
| Tesseract not found | Update `TESSERACT_CMD` in config.py or set env var |

---

*Built for demonstration of sovereign, on-premise agentic AI. All compute stays local.*
