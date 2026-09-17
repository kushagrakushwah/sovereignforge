"""
Agent-level tests — test the full ReAct loop with mocked tools.
These tests do NOT require a real Ollama model.

The loop streams from registry.generate_stream, and dispatches through the
TOOLS dict (which captured the tool functions at import time), so tests mock
generate_stream and patch TOOLS entries with patch.dict.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest

from conftest import make_llm_stream


def _finish(answer: str) -> str:
    return (
        '{"thought": "done", "action": "finish", '
        f'"action_input": {{"answer": "{answer}", "artifacts": []}}, "observation": null}}'
    )


async def _collect(agen, limit: int = 500):
    events = []
    async for event in agen:
        events.append(event)
        if len(events) > limit:
            break
    return events


class TestAgentEventTypes:
    """Test that the agent yields proper event types."""

    @pytest.mark.asyncio
    async def test_agent_yields_start_event(self):
        """Agent should always yield agent_start as first event."""
        from agent.loop import run_agent

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate_stream = make_llm_stream([_finish("Task complete")])
            events = await _collect(run_agent(
                user_input="test task", task_type="document", model_key="reasoning",
            ))

        assert events[0].type == "agent_start"
        assert events[0].data["task_type"] == "document"

    @pytest.mark.asyncio
    async def test_agent_yields_thinking_event(self):
        """Agent should yield a thinking event each iteration."""
        from agent.loop import run_agent

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate_stream = make_llm_stream([_finish("done")])
            events = await _collect(run_agent(
                user_input="test", task_type="coding", model_key="coding",
            ))

        assert "thinking" in [e.type for e in events]

    @pytest.mark.asyncio
    async def test_agent_streams_token_chunks(self):
        """Every streamed chunk is forwarded as a token_chunk event."""
        from agent.loop import run_agent

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate_stream = make_llm_stream([_finish("done")])
            events = await _collect(run_agent(
                user_input="test", task_type="document", model_key="reasoning",
            ))

        chunks = [e.data["token"] for e in events if e.type == "token_chunk"]
        assert len(chunks) > 1
        assert "".join(chunks) == _finish("done")

    @pytest.mark.asyncio
    async def test_agent_passes_conversation_as_messages(self):
        """The loop hands the chat message list (not a flattened string) to the registry."""
        from agent.loop import run_agent

        seen = []
        stream = make_llm_stream([_finish("done")])

        async def spy(model_key, prompt, **kwargs):
            seen.append((model_key, prompt, kwargs))
            async for chunk in stream():
                yield chunk

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate_stream = spy
            await _collect(run_agent(
                user_input="hello", task_type="document", model_key="reasoning",
            ))

        model_key, prompt, kwargs = seen[0]
        assert model_key == "reasoning"
        assert prompt == [{"role": "user", "content": "hello"}]
        assert "system" in kwargs

    @pytest.mark.asyncio
    async def test_agent_finishes_on_finish_action(self):
        """Agent should emit finish event and stop when action=finish."""
        from agent.loop import run_agent

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate_stream = make_llm_stream([_finish("The answer is 42")])
            events = await _collect(run_agent(
                user_input="test", task_type="document", model_key="reasoning",
            ))

        assert events[-1].type == "finish"
        assert events[-1].data["answer"] == "The answer is 42"

    @pytest.mark.asyncio
    async def test_agent_calls_tool_and_feeds_result_back(self, allowed_path):
        """Agent should call a tool, get result, then continue."""
        from agent.loop import run_agent

        pdf = allowed_path("test.pdf")
        ocr_call = (
            '{"thought": "need to OCR", "action": "ocr", '
            f'"action_input": {{"file_path": "{pdf}"}}, "observation": null}}'
        )
        mock_ocr = AsyncMock(return_value={"success": True, "text": "Sample text", "pages": 1, "error": None})

        seen_prompts = []
        stream = make_llm_stream([ocr_call, _finish("OCR complete")])

        async def spy(model_key, prompt, **kwargs):
            seen_prompts.append([dict(m) for m in prompt])
            async for chunk in stream():
                yield chunk

        with patch("agent.loop.registry") as mock_registry, \
             patch.dict("agent.loop.TOOLS", {"ocr": mock_ocr}):
            mock_registry.generate_stream = spy
            events = await _collect(run_agent(
                user_input="read this PDF", task_type="document",
                model_key="reasoning", file_path=pdf,
            ))

        types = [e.type for e in events]
        assert types.index("tool_call") < types.index("tool_result") < types.index("finish")
        mock_ocr.assert_awaited_once_with(file_path=pdf)
        # Second LLM turn must include the tool output as a user message
        assert "Sample text" in seen_prompts[1][-1]["content"]
        assert seen_prompts[1][-2]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_agent_handles_invalid_json_and_recovers(self):
        """Agent should report bad JSON, then recover once the model complies."""
        from agent.loop import run_agent

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate_stream = make_llm_stream([
                "This is not valid JSON at all",
                "Still not JSON",
                _finish("recovered"),
            ])
            events = await _collect(run_agent(
                user_input="test", task_type="document", model_key="reasoning",
            ))

        types = [e.type for e in events]
        assert types.count("error") == 2
        assert events[-1].type == "finish"
        assert events[-1].data["answer"] == "recovered"

    @pytest.mark.asyncio
    async def test_agent_hits_max_iterations(self, allowed_path):
        """Agent should stop and emit max_iterations event."""
        from agent.loop import run_agent
        from config import MAX_AGENT_ITERATIONS

        pdf = allowed_path("x.pdf")
        call = (
            '{"thought": "still thinking", "action": "ocr", '
            f'"action_input": {{"file_path": "{pdf}"}}, "observation": null}}'
        )
        mock_ocr = AsyncMock(return_value={"success": True, "text": "text", "pages": 1, "error": None})

        with patch("agent.loop.registry") as mock_registry, \
             patch.dict("agent.loop.TOOLS", {"ocr": mock_ocr}):
            mock_registry.generate_stream = make_llm_stream([call])
            events = await _collect(run_agent(
                user_input="test", task_type="document",
                model_key="reasoning", file_path=pdf,
            ))

        assert events[-1].type == "max_iterations"
        assert mock_ocr.await_count == MAX_AGENT_ITERATIONS

    @pytest.mark.asyncio
    async def test_agent_rejects_unknown_tool(self):
        """Agent should report an unknown tool name, then continue."""
        from agent.loop import run_agent

        bad_tool = '{"thought": "try this", "action": "nonexistent_tool", "action_input": {}, "observation": null}'

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate_stream = make_llm_stream([bad_tool, _finish("done")])
            events = await _collect(run_agent(
                user_input="test", task_type="document", model_key="reasoning",
            ))

        errors = [e for e in events if e.type == "error"]
        assert len(errors) == 1
        assert "nonexistent_tool" in errors[0].data["message"]
        assert events[-1].type == "finish"

    @pytest.mark.asyncio
    async def test_agent_guardrail_blocks_path_outside_allowed_roots(self):
        """A tool call on a path outside the allowed roots is blocked, not dispatched."""
        from agent.loop import run_agent

        call = '{"thought": "x", "action": "ocr", "action_input": {"file_path": "/etc/passwd"}, "observation": null}'
        mock_ocr = AsyncMock()

        with patch("agent.loop.registry") as mock_registry, \
             patch.dict("agent.loop.TOOLS", {"ocr": mock_ocr}):
            mock_registry.generate_stream = make_llm_stream([call, _finish("done")])
            events = await _collect(run_agent(
                user_input="test", task_type="document", model_key="reasoning",
            ))

        types = [e.type for e in events]
        assert "guardrail_block" in types
        assert "tool_call" not in types
        mock_ocr.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_agent_filters_hallucinated_artifacts(self):
        """finish only reports artifacts that exist in OUTPUT_DIR."""
        from agent.loop import run_agent
        from config import OUTPUT_DIR

        real = Path(OUTPUT_DIR) / "sf_test_real_artifact.docx"
        real.write_bytes(b"x")
        finish = (
            '{"thought": "done", "action": "finish", "action_input": '
            '{"answer": "ok", "artifacts": ["sf_test_real_artifact.docx", "made_up.pptx"]}, '
            '"observation": null}'
        )
        try:
            with patch("agent.loop.registry") as mock_registry:
                mock_registry.generate_stream = make_llm_stream([finish])
                events = await _collect(run_agent(
                    user_input="test", task_type="document", model_key="reasoning",
                ))
        finally:
            real.unlink()

        assert events[-1].data["artifacts"] == ["sf_test_real_artifact.docx"]

    @pytest.mark.asyncio
    async def test_agent_reports_llm_failure(self):
        """An exception from the model stream ends the run with an error event."""
        from agent.loop import run_agent

        async def boom(*args, **kwargs):
            raise ConnectionError("ollama down")
            yield  # pragma: no cover — makes this an async generator

        with patch("agent.loop.registry") as mock_registry:
            mock_registry.generate_stream = boom
            events = await _collect(run_agent(
                user_input="test", task_type="document", model_key="reasoning",
            ))

        assert events[-1].type == "error"
        assert "ollama down" in events[-1].data["message"]
