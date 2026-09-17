"""
Agent ReAct Loop — core of SovereignForge

Implements the Reason + Act loop:
  1. Send context to LLM
  2. Parse LLM's JSON response (thought + action)
  3. Execute the requested tool
  4. Feed result back to LLM
  5. Repeat until action == "finish" or max iterations

Yields AgentEvent objects that are streamed to the UI via WebSocket.
"""
import sys
import json
import re
import asyncio
import inspect
from typing import AsyncGenerator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.registry import registry
from agent.prompts import AGENT_SYSTEM_PROMPT
from tools.ocr import run_ocr
from tools.extract import run_extract
from tools.draft_word import run_draft_word
from tools.draft_ppt import run_draft_ppt
from tools.draft_excel import run_draft_excel
from tools.code_sandbox import run_code_sandbox
from tools.image_understand import run_image_understand
from tools.knowledge_base import run_search_kb, run_ingest_file
from config import MAX_AGENT_ITERATIONS, OUTPUT_DIR
from schemas import AgentEvent
import time
from guardrails.input_guard import check_tool_args, check_artifacts, GuardViolation

# ── Tool dispatch table ──
TOOLS: dict = {
    "ocr":              run_ocr,
    "extract":          run_extract,
    "draft_word":       run_draft_word,
    "draft_ppt":        run_draft_ppt,
    "draft_excel":      run_draft_excel,
    "code_sandbox":     run_code_sandbox,
    "image_understand": run_image_understand,
    "search_kb":        run_search_kb,
    "ingest_file":      run_ingest_file,
}


async def run_agent(
    user_input: str,
    task_type: str,
    model_key: str,
    file_path: str = None,
) -> AsyncGenerator[AgentEvent, None]:
    """
    Main ReAct agent loop.

    Yields AgentEvent objects (streamed to frontend via WebSocket).

    Args:
        user_input: The user's raw request string
        task_type:  "document" | "coding" | "multimodal"
        model_key:  "reasoning" | "coding" | "vision"
        file_path:  Optional absolute path to uploaded file
    """
    # ── Build initial context ──
    file_context = f"\nUploaded file available at: {file_path}" if file_path else ""
    initial_message = f"{user_input}{file_context}"

    # Conversation history (user/assistant turns)
    conversation: list[dict] = [{"role": "user", "content": initial_message}]

    yield AgentEvent(type="agent_start", data={
        "task_type": task_type,
        "model": model_key,
        "message": f"Starting {task_type} task with {model_key} model...",
    })

    _start_time = time.monotonic()

    for iteration in range(MAX_AGENT_ITERATIONS):
        yield AgentEvent(type="thinking", data={
            "iteration": iteration + 1,
            "message": f"Thinking... (step {iteration + 1}/{MAX_AGENT_ITERATIONS})",
        })

        # ── Call LLM (with streaming for live token output) ──
        raw_response = ""
        try:
            async for token in registry.generate_stream(
                model_key,
                conversation,
                system=AGENT_SYSTEM_PROMPT,
            ):
                raw_response += token
                yield AgentEvent(type="token_chunk", data={
                    "token": token,
                    "iteration": iteration + 1,
                })
        except Exception as exc:
            yield AgentEvent(type="error", data={
                "message": f"LLM call failed: {str(exc)}",
            })
            return

        # ── Parse LLM response ──
        parsed = _parse_llm_response(raw_response)

        if parsed is None:
            yield AgentEvent(type="error", data={
                "message": "Failed to parse LLM JSON response",
                "raw": raw_response[:500],
            })
            # Try to recover — add a correction message
            conversation.append({"role": "assistant", "content": raw_response})
            conversation.append({
                "role": "user",
                "content": (
                    "ERROR: Your response was not valid JSON. "
                    "You MUST respond with the exact JSON format specified in the system prompt. "
                    "Try again."
                ),
            })
            continue

        thought = parsed.get("thought", "")
        action = parsed.get("action", "")
        action_input = parsed.get("action_input", {})

        yield AgentEvent(type="thought", data={
            "thought": thought,
            "action": action,
            "iteration": iteration + 1,
        })

        # ── Handle FINISH ──
        if action == "finish":
            answer = action_input.get("answer", "Task complete.")
            raw_artifacts = action_input.get("artifacts", [])
            # Validate artifacts actually exist on disk (prevent hallucination)
            valid_artifacts = check_artifacts(raw_artifacts, OUTPUT_DIR)
            yield AgentEvent(type="finish", data={
                "answer": answer,
                "artifacts": valid_artifacts,
                "total_elapsed_s": round(time.monotonic() - _start_time, 2),
            })
            return

        # ── Validate tool name ──
        if action not in TOOLS:
            yield AgentEvent(type="error", data={
                "message": f"Unknown tool: '{action}'. Valid tools: {list(TOOLS.keys())}",
            })
            # Inject correction and let agent retry
            conversation.append({"role": "assistant", "content": raw_response})
            conversation.append({
                "role": "user",
                "content": (
                    f"ERROR: Tool '{action}' does not exist. "
                    f"Valid tools are: {list(TOOLS.keys())}. Try again."
                ),
            })
            continue

        # ── Guardrail: check tool arguments before dispatch ──────────────────
        try:
            check_tool_args(action, action_input)
        except GuardViolation as gv:
            yield AgentEvent(type="guardrail_block", data={
                "category": gv.category,
                "message": gv.reason,
                "tool": action,
            })
            conversation.append({"role": "assistant", "content": raw_response})
            conversation.append({
                "role": "user",
                "content": f"GUARDRAIL BLOCK: {gv.reason}. Choose a different approach.",
            })
            continue

        # ── Execute tool (with timing) ────────────────────────────────────────
        _tool_start = time.monotonic()
        yield AgentEvent(type="tool_call", data={
            "tool": action,
            "input": action_input,
            "message": f"Calling {action}...",
            "elapsed_s": round(time.monotonic() - _start_time, 2),
        })

        try:
            tool_fn = TOOLS[action]
            tool_result = await _call_tool(tool_fn, action_input)
        except TypeError as exc:
            tool_result = {
                "success": False,
                "error": f"Bad arguments for '{action}': {str(exc)}",
            }
        except Exception as exc:
            tool_result = {"success": False, "error": str(exc)}

        _tool_elapsed = round(time.monotonic() - _tool_start, 2)
        yield AgentEvent(type="tool_result", data={
            "tool": action,
            "result": _truncate_result(tool_result),
            "success": bool(tool_result.get("success", False)),
            "elapsed_s": _tool_elapsed,
            "total_elapsed_s": round(time.monotonic() - _start_time, 2),
        })

        # ── Feed result back into conversation ──
        conversation.append({"role": "assistant", "content": raw_response})
        result_summary = json.dumps(_truncate_result(tool_result, max_chars=2000))
        conversation.append({
            "role": "user",
            "content": (
                f"Tool '{action}' returned:\n{result_summary}\n\n"
                "Continue with the next step."
            ),
        })

    # ── Hit max iterations ──
    yield AgentEvent(type="max_iterations", data={
        "message": (
            f"Reached maximum iterations ({MAX_AGENT_ITERATIONS}). "
            "Stopping. Please try a simpler task or increase MAX_AGENT_ITERATIONS."
        ),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_llm_response(raw: str) -> dict | None:
    """
    Robustly extract a JSON object from the LLM's response.
    Handles:
      - Direct JSON
      - Markdown fenced blocks
      - JSON embedded in prose text
    """
    if not raw or not raw.strip():
        return None

    # 1. Direct parse
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences
    clean = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # 3. Find JSON object in text
    match = re.search(r'\{[\s\S]*"action"[\s\S]*\}', raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 4. Find any JSON object
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


async def _call_tool(tool_fn, action_input: dict):
    """Dispatch tool call with the provided arguments."""
    if inspect.iscoroutinefunction(tool_fn):
        return await tool_fn(**action_input)
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: tool_fn(**action_input))


def _truncate_result(result: dict, max_chars: int = 500) -> dict:
    """Truncate long string values in a result dict for logging/UI."""
    truncated = {}
    for k, v in result.items():
        if isinstance(v, str) and len(v) > max_chars:
            truncated[k] = v[:max_chars] + f"... [{len(v) - max_chars} chars truncated]"
        else:
            truncated[k] = v
    return truncated
