"""
input_guard.py — Rule-based input/output guardrails for SovereignForge.

Provides three guards:
  1. check_user_input()  — run before the agent loop starts
  2. check_tool_args()   — run before each tool is dispatched
  3. check_artifacts()   — validate finish-event artifacts against disk

All checks are pure-Python regex/string — no LLM call required.
Designed for industrial deployments (MRPL context): blocks prompt injection,
path traversal, data-exfiltration patterns, and over-long inputs.
"""
from __future__ import annotations

import re
from pathlib import Path

# ── Limits ────────────────────────────────────────────────────────────────────
MAX_INPUT_CHARS = 8_000       # ~2000 tokens for 7B models
MAX_FILE_PATH_CHARS = 512

# ── Injection / jailbreak patterns ────────────────────────────────────────────
# Patterns indicating prompt-injection or jailbreak attempts.
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.I),
    re.compile(r"disregard\s+(your|the)\s+(system|previous)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"DAN\s+mode", re.I),
    re.compile(r"\bpretend\s+(you|to)\b", re.I),
    re.compile(r"<\s*system\s*>", re.I),           # XML-style injection
    re.compile(r"\[INST\]|\[/INST\]", re.I),        # Llama-style injection
]

# ── Data-exfiltration patterns ────────────────────────────────────────────────
# Patterns suggesting user wants to send data outside (impossible with the
# mitmproxy setup, but blocked at the prompt level as defence-in-depth).
_EXFILTRATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"send\s+(to|via|through)\s+(email|smtp|http|ftp|telegram|slack|whatsapp)", re.I),
    re.compile(r"upload\s+to\s+(cloud|s3|gcs|azure|dropbox|drive)", re.I),
    re.compile(r"post\s+to\s+(api|url|endpoint|server)", re.I),
    re.compile(r"exfiltrate", re.I),
]

# ── Path traversal patterns ───────────────────────────────────────────────────
_PATH_TRAVERSAL: list[re.Pattern] = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.[\\\\]"),
    re.compile(r"%2e%2e", re.I),
    re.compile(r"\x00"),   # null byte injection
]

# ── Allowed root directories for file tool arguments ──────────────────────────
# Defined in config.py (TEMP_BASE plus anything listed in SF_ALLOWED_PATHS).
from config import ALLOWED_FILE_ROOTS


class GuardViolation(Exception):
    """
    Raised when a guardrail check fails.
    Caught by main.py / loop.py and returned as a 'guardrail_block' event.
    """
    def __init__(self, reason: str, category: str):
        super().__init__(reason)
        self.reason = reason
        self.category = category  # "injection" | "exfiltration" | "path_traversal" | "length"


def check_user_input(user_input: str) -> None:
    """
    Validate raw user input before the agent loop starts.
    Raises GuardViolation with a human-readable reason if any check fails.
    """
    # 1. Length check
    if len(user_input) > MAX_INPUT_CHARS:
        raise GuardViolation(
            f"Input too long ({len(user_input)} chars). Maximum allowed is {MAX_INPUT_CHARS}.",
            category="length",
        )

    # 2. Prompt injection check
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(user_input):
            raise GuardViolation(
                f"Potential prompt injection detected. Please rephrase your request.",
                category="injection",
            )

    # 3. Exfiltration check
    for pattern in _EXFILTRATION_PATTERNS:
        if pattern.search(user_input):
            raise GuardViolation(
                "Data exfiltration pattern detected. This system is air-gapped and cannot send data externally.",
                category="exfiltration",
            )


def check_tool_args(tool_name: str, action_input: dict) -> None:
    """
    Validate tool arguments before tool dispatch.
    Checks any file_path-style arguments for path traversal and sandbox escapes.
    Raises GuardViolation if any check fails.
    """
    file_args = [
        v for k, v in action_input.items()
        if isinstance(v, str) and ("path" in k.lower() or "file" in k.lower())
    ]

    for fp in file_args:
        if len(fp) > MAX_FILE_PATH_CHARS:
            raise GuardViolation(
                f"File path too long in tool '{tool_name}'.",
                category="path_traversal",
            )
        for pattern in _PATH_TRAVERSAL:
            if pattern.search(fp):
                raise GuardViolation(
                    f"Path traversal attempt detected in tool '{tool_name}'.",
                    category="path_traversal",
                )
        # Must be inside an allowed directory. resolve(strict=False) works for
        # paths that don't exist yet; an unresolvable path is rejected.
        try:
            resolved = Path(fp).resolve()
        except (OSError, ValueError, RuntimeError):
            raise GuardViolation(
                f"Unresolvable file path in tool '{tool_name}'.",
                category="path_traversal",
            )
        if not any(resolved.is_relative_to(root) for root in ALLOWED_FILE_ROOTS):
            raise GuardViolation(
                f"File path outside allowed directories in tool '{tool_name}': {resolved.name}",
                category="path_traversal",
            )


def check_artifacts(artifacts: list, output_dir: str) -> list[str]:
    """
    Filter artifact list to only basenames that actually exist in output_dir.
    Used in the agent loop before emitting the 'finish' event to prevent
    the agent from reporting hallucinated filenames.

    Returns:
        List of valid (existing) artifact filenames.
    """
    valid = []
    for artifact in artifacts:
        if not isinstance(artifact, str):
            continue
        # Only take basename — prevents any directory component
        name = Path(artifact).name
        full_path = Path(output_dir) / name
        if full_path.exists():
            valid.append(name)
    return valid
