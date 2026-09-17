"""
test_hardening.py — Regression tests for the Ollama chat migration and the
cache / guardrail / sovereignty fixes. No Ollama, Docker or Tesseract needed.
"""
import sys
import json
import types
import importlib
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import httpx
import pytest


# ─────────────────────────────────────────────────────────────────────────────
#  Semantic cache — exact vs semantic matching
# ─────────────────────────────────────────────────────────────────────────────

class TestSemanticCacheSafety:

    def test_long_prompts_never_match_semantically(self):
        """Two long prompts that embed identically (MiniLM truncation) must not collide."""
        from cache.semantic_cache import SemanticCache
        c = SemanticCache(max_semantic_chars=100)
        header = "INSPECTION REPORT — MRPL letterhead " * 10
        with patch("cache.semantic_cache._embed", return_value=[1.0, 0.0]) as emb:
            c.put("reasoning", header + "document A", "extraction A")
            assert c.get("reasoning", header + "document B") is None
        emb.assert_not_called()  # long prompts are never embedded
        assert c.misses == 1

    def test_long_prompt_exact_hit(self):
        from cache.semantic_cache import SemanticCache
        c = SemanticCache(max_semantic_chars=10)
        prompt = "x" * 500
        c.put("reasoning", prompt, "answer")
        assert c.get("reasoning", prompt) == "answer"
        assert c.exact_hits == 1 and c.semantic_hits == 0

    def test_short_prompt_semantic_hit(self):
        from cache.semantic_cache import SemanticCache
        c = SemanticCache()
        with patch("cache.semantic_cache._embed", return_value=[1.0, 0.0]):
            c.put("reasoning", "what is the flash point of diesel?", "52 °C")
            assert c.get("reasoning", "what's the flash point of diesel") == "52 °C"
        assert c.semantic_hits == 1

    def test_exact_hit_respects_model_key(self):
        from cache.semantic_cache import SemanticCache
        c = SemanticCache(max_semantic_chars=0)
        c.put("coding", "same", "code answer")
        assert c.get("reasoning", "same") is None

    def test_embedding_failure_still_allows_exact_hits(self):
        from cache.semantic_cache import SemanticCache
        c = SemanticCache()
        with patch("cache.semantic_cache._embed", side_effect=RuntimeError("no model")):
            c.put("reasoning", "short prompt", "answer")
            assert c.get("reasoning", "short prompt") == "answer"
            assert c.get("reasoning", "different prompt") is None

    def test_stats_split_hits(self):
        from cache.semantic_cache import SemanticCache
        stats = SemanticCache().stats()
        assert {"exact_hits", "semantic_hits"} <= stats.keys()


# ─────────────────────────────────────────────────────────────────────────────
#  Model registry — /api/chat payloads and streaming cache
# ─────────────────────────────────────────────────────────────────────────────

class _FakeOllama:
    """Captures requests and replies like Ollama's /api/chat."""

    def __init__(self, reply="hello world", stream_parts=None, finish_stream=True):
        self.requests = []
        self.reply = reply
        self.stream_parts = stream_parts or ["hel", "lo ", "world"]
        self.finish_stream = finish_stream

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append((request.url.path, body))
        if body.get("stream"):
            lines = [json.dumps({"message": {"content": p}, "done": False}) for p in self.stream_parts]
            if self.finish_stream:
                lines.append(json.dumps({"message": {"content": ""}, "done": True}))
            return httpx.Response(200, text="\n".join(lines) + "\n")
        return httpx.Response(200, json={"message": {"role": "assistant", "content": self.reply}, "done": True})

    def client_factory(self):
        real = httpx.AsyncClient
        transport = httpx.MockTransport(self.handler)
        return lambda *a, **kw: real(*a, transport=transport, **kw)


@pytest.fixture
def fresh_cache():
    from cache.semantic_cache import cache
    cache.clear()
    yield cache
    cache.clear()


class TestRegistryChat:

    @pytest.mark.asyncio
    async def test_generate_uses_chat_endpoint_with_num_ctx(self, fresh_cache):
        from models.registry import registry
        from config import OLLAMA_NUM_CTX
        fake = _FakeOllama(reply="ok")
        with patch("models.registry.httpx.AsyncClient", fake.client_factory()):
            out = await registry.generate("reasoning", "hi", system="SYS", use_cache=False)

        assert out == "ok"
        path, body = fake.requests[0]
        assert path == "/api/chat"
        assert body["options"]["num_ctx"] == OLLAMA_NUM_CTX
        assert body["format"] == "json"
        assert body["messages"] == [
            {"role": "system", "content": "SYS"},
            {"role": "user", "content": "hi"},
        ]

    @pytest.mark.asyncio
    async def test_stream_does_not_mutate_conversation(self, fresh_cache):
        from models.registry import registry
        fake = _FakeOllama()
        conversation = [{"role": "user", "content": "q"}]
        with patch("models.registry.httpx.AsyncClient", fake.client_factory()):
            chunks = [c async for c in registry.generate_stream(
                "reasoning", conversation, system="SYS", use_cache=False)]

        assert "".join(chunks) == "hello world"
        assert fake.requests[0][1]["format"] == "json"
        assert conversation == [{"role": "user", "content": "q"}]
        assert fake.requests[0][1]["messages"][0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_stream_cache_replays_completed_response(self, fresh_cache):
        from models.registry import registry
        fake = _FakeOllama()
        conv = [{"role": "user", "content": "long " * 400}]
        with patch("models.registry.httpx.AsyncClient", fake.client_factory()):
            first = "".join([c async for c in registry.generate_stream("reasoning", conv, system="S")])
            second = [c async for c in registry.generate_stream("reasoning", conv, system="S")]

        assert len(fake.requests) == 1          # second call served from cache
        assert second == [first]                # replayed as one chunk
        assert fresh_cache.exact_hits == 1

    @pytest.mark.asyncio
    async def test_stream_cache_skips_incomplete_response(self, fresh_cache):
        from models.registry import registry
        fake = _FakeOllama(finish_stream=False)
        conv = [{"role": "user", "content": "long " * 400}]
        with patch("models.registry.httpx.AsyncClient", fake.client_factory()):
            [c async for c in registry.generate_stream("reasoning", conv)]
            [c async for c in registry.generate_stream("reasoning", conv)]

        assert len(fake.requests) == 2
        assert fresh_cache.stats()["entries"] == 0

    @pytest.mark.asyncio
    async def test_vision_uses_chat_with_images(self, tmp_path):
        from models.registry import registry
        from config import OLLAMA_NUM_CTX
        img = tmp_path / "a.png"
        img.write_bytes(b"\x89PNGfake")
        fake = _FakeOllama(reply="a diagram")
        with patch("models.registry.httpx.AsyncClient", fake.client_factory()):
            out = await registry.generate_vision("what?", str(img))

        assert out == "a diagram"
        path, body = fake.requests[0]
        assert path == "/api/chat"
        assert body["options"]["num_ctx"] == OLLAMA_NUM_CTX
        assert "format" not in body          # vision answers are free text
        msg = body["messages"][0]
        assert msg["content"] == "what?"
        assert len(msg["images"]) == 1

    @pytest.mark.asyncio
    async def test_text_mode_opt_out_and_separate_cache(self, fresh_cache):
        from models.registry import registry
        fake = _FakeOllama(reply="plain prose")
        with patch("models.registry.httpx.AsyncClient", fake.client_factory()):
            await registry.generate("reasoning", "same prompt", json_mode=True)
            await registry.generate("reasoning", "same prompt", json_mode=False)

        assert "format" in fake.requests[0][1]
        assert "format" not in fake.requests[1][1]
        assert len(fake.requests) == 2      # JSON answer not reused for text mode

    def test_cache_key_is_readable_and_role_aware(self):
        from models.registry import _cache_key
        assert _cache_key([{"role": "user", "content": "hi"}]) == "hi"
        key = _cache_key([{"role": "system", "content": "S"}, {"role": "user", "content": "hi"}])
        assert key == "SYSTEM: S\n\nUSER: hi"
        assert "{" not in key


# ─────────────────────────────────────────────────────────────────────────────
#  Guardrail — path containment
# ─────────────────────────────────────────────────────────────────────────────

class TestPathContainment:

    def test_sibling_directory_with_shared_prefix_is_blocked(self):
        from guardrails.input_guard import check_tool_args, GuardViolation
        from config import TEMP_BASE
        sibling = str(TEMP_BASE.resolve()) + "-evil/x.pdf"
        with pytest.raises(GuardViolation):
            check_tool_args("ocr", {"file_path": sibling})

    def test_nonexistent_path_inside_root_is_allowed(self):
        from guardrails.input_guard import check_tool_args
        from config import UPLOAD_DIR
        check_tool_args("ocr", {"file_path": str(Path(UPLOAD_DIR) / "not_yet_created.pdf")})

    def test_absolute_path_outside_root_is_blocked(self):
        from guardrails.input_guard import check_tool_args, GuardViolation
        with pytest.raises(GuardViolation):
            check_tool_args("ingest_file", {"file_path": "/etc/passwd"})

    def test_extra_root_is_allowed(self, tmp_path):
        from guardrails import input_guard
        doc = tmp_path / "sop.txt"
        with patch.object(input_guard, "ALLOWED_FILE_ROOTS", [str(tmp_path.resolve())]):
            input_guard.check_tool_args("ingest_file", {"file_path": str(doc)})

    def test_sf_allowed_paths_env_is_parsed(self, tmp_path, monkeypatch):
        import os
        import config
        extra = tmp_path / "sop_library"
        monkeypatch.setenv("SF_ALLOWED_PATHS", os.pathsep.join([str(extra), ""]))
        try:
            reloaded = importlib.reload(config)
            assert str(extra.resolve()) in reloaded.ALLOWED_FILE_ROOTS
            assert str(reloaded.TEMP_BASE.resolve()) == reloaded.ALLOWED_FILE_ROOTS[0]
        finally:
            monkeypatch.delenv("SF_ALLOWED_PATHS")
            importlib.reload(config)


# ─────────────────────────────────────────────────────────────────────────────
#  mitmproxy addon — host matching
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def addon(tmp_path, monkeypatch):
    """Import the addon with a stub mitmproxy and a throwaway log dir."""
    http_stub = types.SimpleNamespace(HTTPFlow=object, Response=None)
    monkeypatch.setitem(sys.modules, "mitmproxy", types.SimpleNamespace(http=http_stub))
    monkeypatch.setitem(sys.modules, "mitmproxy.http", http_stub)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    path = Path(__file__).parent.parent / "sovereignty" / "mitmproxy_addon.py"
    spec = importlib.util.spec_from_file_location("sf_mitm_addon_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.addons[0]


class TestSovereigntyHostMatch:

    @pytest.mark.parametrize("host", [
        "localhost", "LOCALHOST", "localhost.", "127.0.0.1", "[::1]", "::1", "host.docker.internal", "ollama",
    ])
    def test_local_hosts(self, addon, host):
        assert addon._is_local(host)

    @pytest.mark.parametrize("host", [
        "localhost.attacker.com", "127.0.0.1.nip.io", "evil-localhost", "huggingface.co", "10.0.0.5",
        "ollama.com", "registry.ollama.ai",
    ])
    def test_lookalike_hosts_are_external(self, addon, host):
        assert not addon._is_local(host)


# ─────────────────────────────────────────────────────────────────────────────
#  BM25 — real IDF
# ─────────────────────────────────────────────────────────────────────────────

class TestBM25Idf:

    def test_rare_term_outweighs_common_term(self):
        from tools.knowledge_base import _bm25_idf, _bm25_score
        corpus = [
            ["valve", "inspection", "oisd"],
            ["valve", "inspection", "pump"],
            ["valve", "inspection", "motor"],
        ]
        idf = _bm25_idf(corpus)
        assert idf["oisd"] > idf["valve"] > 0
        common = _bm25_score(["valve"], corpus[0], 3.0, idf=idf)
        rare = _bm25_score(["oisd"], corpus[0], 3.0, idf=idf)
        assert rare > common

    def test_unknown_query_term_scores_zero(self):
        from tools.knowledge_base import _bm25_idf, _bm25_score
        idf = _bm25_idf([["a", "b"]])
        assert _bm25_score(["zzz"], ["a", "b"], 2.0, idf=idf) == 0.0

    def test_single_document_corpus_still_scores(self):
        from tools.knowledge_base import _bm25_idf, _bm25_score
        idf = _bm25_idf([["earthing", "resistance"]])
        assert _bm25_score(["earthing"], ["earthing", "resistance"], 2.0, idf=idf) > 0
