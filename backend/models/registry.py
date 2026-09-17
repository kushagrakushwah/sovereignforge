"""Model registry — single point of contact for all Ollama calls."""
import json
import httpx
import base64
import sys
from pathlib import Path

# Allow running from backend/ directory directly
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    OLLAMA_BASE_URL, OLLAMA_NUM_CTX, MODELS, MODELS_FALLBACK, LLM_TIMEOUT_SECONDS,
)
from cache.semantic_cache import cache as _semantic_cache


class ModelRegistry:
    """
    Central client for all Ollama model calls.
    Never call Ollama directly from tools — always go through this registry.
    All calls use Ollama's /api/chat so the model's own chat template is applied.
    """

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.models = MODELS
        self.fallback = MODELS_FALLBACK

    async def generate(
        self,
        model_key: str,
        prompt: str | list[dict],
        system: str = None,
        use_cache: bool = True,
        json_mode: bool = True,
    ) -> str:
        """
        Call a text/reasoning model and return the full response.

        Args:
            model_key:  "reasoning" | "coding" | "vision"
            prompt:     A single user prompt, or a list of chat messages
                        ({"role": "user"|"assistant", "content": ...})
            system:     Optional system prompt
            use_cache:  If True (default), check the semantic cache before calling Ollama.
            json_mode:  If True (default), ask Ollama to constrain output to valid JSON.
                        Every current caller (agent loop, extract) parses JSON.

        Returns:
            Full response string from the model.
        """
        messages = _build_messages(prompt, system)
        cache_key = _cache_key(messages)
        cache_ns = model_key if json_mode else f"{model_key}:text"
        if use_cache:
            cached = _semantic_cache.get(cache_ns, cache_key)
            if cached is not None:
                return cached

        payload = self._chat_payload(model_key, messages, stream=False, json_mode=json_mode)

        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            response = resp.json()["message"]["content"]

        if use_cache:
            _semantic_cache.put(cache_ns, cache_key, response)

        return response

    async def generate_stream(
        self,
        model_key: str,
        prompt: str | list[dict],
        system: str = None,
        use_cache: bool = True,
        json_mode: bool = True,
    ):
        """
        Streaming version of generate() — yields text chunks as they arrive from Ollama.
        Used by the agent loop to emit token_chunk WebSocket events for a live typewriter effect.

        On a cache hit the cached response is yielded as a single chunk. A fully
        streamed response is stored in the cache; an interrupted one is not.

        Yields:
            str: Each text chunk from the streaming Ollama response.
        """
        messages = _build_messages(prompt, system)
        cache_key = _cache_key(messages)
        cache_ns = model_key if json_mode else f"{model_key}:text"
        if use_cache:
            cached = _semantic_cache.get(cache_ns, cache_key)
            if cached is not None:
                yield cached
                return

        payload = self._chat_payload(model_key, messages, stream=True, json_mode=json_mode)
        chunks: list[str] = []
        completed = False

        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk_data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk_data.get("message", {}).get("content", "")
                    if token:
                        chunks.append(token)
                        yield token
                    if chunk_data.get("done", False):
                        completed = True
                        break

        if use_cache and completed:
            _semantic_cache.put(cache_ns, cache_key, "".join(chunks))

    async def generate_vision(self, prompt: str, image_path: str) -> str:
        """
        Call the vision model with a local image file.

        Args:
            prompt:     Description / question about the image
            image_path: Absolute path to a .jpg/.png file

        Returns:
            Model analysis string.
        """
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        messages = [{"role": "user", "content": prompt, "images": [image_b64]}]
        payload = self._chat_payload("vision", messages, stream=False)

        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def health_check(self) -> dict:
        """Return list of locally available Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return {"status": "ok", "models": resp.json().get("models", [])}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _chat_payload(
        self, model_key: str, messages: list[dict], stream: bool, json_mode: bool = False,
    ) -> dict:
        payload = {
            "model": self._resolve_model(model_key),
            "messages": messages,
            "stream": stream,
            "options": {"num_ctx": OLLAMA_NUM_CTX},
        }
        if json_mode:
            payload["format"] = "json"
        return payload

    def _resolve_model(self, model_key: str) -> str:
        """Return model name string for the given key."""
        if model_key not in self.models:
            raise ValueError(f"Unknown model key: {model_key!r}. "
                             f"Valid keys: {list(self.models.keys())}")
        return self.models[model_key]

    def get_cache_stats(self) -> dict:
        """Return semantic cache statistics."""
        return _semantic_cache.stats()


def _build_messages(prompt: str | list[dict], system: str | None) -> list[dict]:
    """Normalise a prompt into an Ollama chat message list (never mutates the input)."""
    if isinstance(prompt, str):
        messages = [{"role": "user", "content": prompt}]
    else:
        messages = [dict(m) for m in prompt]
    if system:
        messages.insert(0, {"role": "system", "content": system})
    return messages


def _cache_key(messages: list[dict]) -> str:
    """
    Readable, deterministic cache key for a message list.
    A lone user message is keyed by its bare text so short prompts stay
    eligible for semantic matching.
    """
    if len(messages) == 1:
        return messages[0]["content"]
    return "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)


# ── Singleton — import this from everywhere ──
registry = ModelRegistry()
