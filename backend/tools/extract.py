"""Extract Tool — use LLM to extract structured information from raw text."""
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.registry import registry

EXTRACT_SYSTEM_PROMPT = (
    "You are a precise document analysis assistant. "
    "Extract structured information exactly as requested. "
    "Always respond with valid JSON only. "
    "No preamble, no explanation, no markdown fences."
)

WINDOW_SIZE = 5000    # chars per window
WINDOW_OVERLAP = 500  # overlap between windows


def _sliding_windows(text: str) -> list[str]:
    """Split long text into overlapping windows for multi-pass extraction."""
    if len(text) <= WINDOW_SIZE:
        return [text]
    windows = []
    i = 0
    while i < len(text):
        windows.append(text[i: i + WINDOW_SIZE])
        i += WINDOW_SIZE - WINDOW_OVERLAP
    return windows


def _merge_extractions(extractions: list[dict]) -> dict:
    """Merge multiple window extractions into a single coherent result."""
    merged_findings: list[str] = []
    merged_risks: list[str] = []
    merged_recommendations: list[str] = []
    summaries: list[str] = []

    for ext in extractions:
        if not ext.get("success"):
            continue
        summaries.append(ext.get("summary", ""))
        merged_findings.extend(ext.get("findings", []))
        merged_risks.extend(ext.get("risks", []))
        merged_recommendations.extend(ext.get("recommendations", []))

    # Deduplicate (simple: remove exact duplicates)
    def dedupe(lst: list[str]) -> list[str]:
        seen = set()
        out = []
        for item in lst:
            key = item.strip().lower()[:80]
            if key and key not in seen:
                seen.add(key)
                out.append(item)
        return out

    return {
        "success": True,
        "summary": " ".join(s for s in summaries if s)[:600],
        "findings": dedupe(merged_findings),
        "risks": dedupe(merged_risks),
        "recommendations": dedupe(merged_recommendations),
        "raw_json": {},
        "windows_processed": len(extractions),
    }


def _build_extract_prompt(text: str, extraction_goal: str) -> str:
    """Build the extraction prompt for a single text window."""
    return f"""Extract the following from this document text: {extraction_goal}

DOCUMENT TEXT:
{text}

Respond ONLY with a valid JSON object with these exact keys:
{{
  "summary": "2-3 sentence overview of this section",
  "findings": ["finding 1", "finding 2"],
  "risks": ["risk 1", "risk 2"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}}

No other text. No markdown. Just the JSON object."""


async def run_extract(
    raw_text: str,
    extraction_goal: str = "key findings, risks, and recommendations",
) -> dict:
    """
    Extract structured information from raw text using the reasoning LLM.

    Args:
        raw_text:         The source text (e.g., from OCR)
        extraction_goal:  Human description of what to pull out

    Returns:
        {
            "success": bool,
            "summary": str,
            "findings": list[str],
            "risks": list[str],
            "recommendations": list[str],
            "raw_json": dict
        }
    """
    # ── Single window (short document) ───────────────────────────────────────
    if len(raw_text) <= WINDOW_SIZE:
        prompt = _build_extract_prompt(raw_text, extraction_goal)
        try:
            response = await registry.generate("reasoning", prompt, system=EXTRACT_SYSTEM_PROMPT)
        except Exception as exc:
            return _failure(str(exc))
        return _parse_response(response)

    # ── Multi-window (long document) ─────────────────────────────────────────
    windows = _sliding_windows(raw_text)
    # Limit to 6 windows max to avoid excessive LLM calls
    windows = windows[:6]

    extractions = []
    for i, window in enumerate(windows):
        prompt = _build_extract_prompt(
            window,
            f"{extraction_goal} (document section {i+1}/{len(windows)})",
        )
        try:
            response = await registry.generate("reasoning", prompt, system=EXTRACT_SYSTEM_PROMPT)
            extractions.append(_parse_response(response))
        except Exception:
            continue  # skip failed windows, continue with rest

    if not extractions:
        return _failure("All extraction windows failed.")

    return _merge_extractions(extractions)



def _parse_response(response: str) -> dict:
    """Parse LLM JSON response with robust fallback handling."""
    # Try direct JSON parse
    try:
        clean = response.strip()
        parsed = json.loads(clean)
        return _build_success(parsed)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    clean = re.sub(r"```(?:json)?|```", "", response).strip()
    try:
        parsed = json.loads(clean)
        return _build_success(parsed)
    except json.JSONDecodeError:
        pass

    # Find first JSON object in string
    match = re.search(r"\{[\s\S]*\}", response)
    if match:
        try:
            parsed = json.loads(match.group())
            return _build_success(parsed)
        except json.JSONDecodeError:
            pass

    # Complete fallback — return raw text as single finding
    return {
        "success": False,
        "summary": response[:300],
        "findings": [response] if response else [],
        "risks": [],
        "recommendations": [],
        "raw_json": {},
        "error": "Failed to parse LLM JSON response",
    }


def _build_success(parsed: dict) -> dict:
    return {
        "success": True,
        "summary": parsed.get("summary", ""),
        "findings": _ensure_list(parsed.get("findings", [])),
        "risks": _ensure_list(parsed.get("risks", [])),
        "recommendations": _ensure_list(parsed.get("recommendations", [])),
        "raw_json": parsed,
    }


def _failure(error: str) -> dict:
    return {
        "success": False,
        "summary": "",
        "findings": [],
        "risks": [],
        "recommendations": [],
        "raw_json": {},
        "error": error,
    }


def _ensure_list(val) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []
