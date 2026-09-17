"""
SovereignForge Configuration
All constants live here. Every other module imports from this file.
Windows-compatible paths using tempfile.gettempdir().
"""
import os
import tempfile
from pathlib import Path

# ── Base directories ──
TEMP_BASE = Path(tempfile.gettempdir()) / "sovereignforge"
UPLOAD_DIR = str(TEMP_BASE / "uploads")
OUTPUT_DIR = str(TEMP_BASE / "outputs")
NETWORK_LOG_PATH = str(TEMP_BASE / "network.log")

# Create dirs on import
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Ollama ──
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

MODELS = {
    # Use quantized versions for 6–8 GB VRAM
    "reasoning": os.getenv("MODEL_REASONING", "qwen2.5:7b-instruct-q4_K_M"),
    "coding":    os.getenv("MODEL_CODING",    "qwen2.5-coder:7b-instruct-q4_K_M"),
    "vision":    os.getenv("MODEL_VISION",    "qwen2.5vl:7b"),
}

# Context window passed to Ollama. Ollama's default (2048) silently truncates
# the ReAct conversation once OCR text and KB hits accumulate.
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

# Fallback model names (if quantized not available)
MODELS_FALLBACK = {
    "reasoning": "qwen2.5:7b",
    "coding":    "qwen2.5-coder:7b",
    "vision":    "qwen2.5vl:7b",
}

# ── Task types ──
TASK_TYPES = ["document", "coding", "multimodal"]

# ── Docker sandbox ──
SANDBOX_IMAGE = "sovereignforge-sandbox:latest"
SANDBOX_TIMEOUT = 30          # seconds
SANDBOX_MEMORY_LIMIT = "256m"
SANDBOX_CPU_QUOTA = 500_000_000  # 0.5 CPU (nanocpus)

# ── OCR ──
# Tesseract path — Windows default install location
TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
OCR_DPI = 200

# ── mitmproxy ──
MITMPROXY_LOG_PATH = NETWORK_LOG_PATH
MITMPROXY_PORT = 8080

# ── Ports ──
BACKEND_PORT = 8000
FRONTEND_PORT = 3000

# ── Agent ──
MAX_AGENT_ITERATIONS = 12
LLM_TIMEOUT_SECONDS = 600   # Increased to 10 minutes for large context processing (OCR + KB)

# ── Knowledge Base ──
KB_DIR = str(TEMP_BASE / "knowledge_base")
os.makedirs(KB_DIR, exist_ok=True)

# ── Guardrails ──
# Roots that agent tools may read from / write to. TEMP_BASE covers uploads,
# outputs and the KB. Extra roots (e.g. an SOP library) can be added with
# SF_ALLOWED_PATHS, separated by os.pathsep (":" on Linux, ";" on Windows).
ALLOWED_FILE_ROOTS = [str(TEMP_BASE.resolve())] + [
    str(Path(p).resolve())
    for p in os.getenv("SF_ALLOWED_PATHS", "").split(os.pathsep)
    if p.strip()
]

# ── Allowed local hosts (sovereignty check) ──
# "ollama" is the docker-compose service name; it only resolves inside the stack network.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal", "ollama"}
