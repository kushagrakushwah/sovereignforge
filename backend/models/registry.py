"""Model registry — single point of contact for all Ollama calls."""
import json
import httpx
import base64
import sys
import os
from pathlib import Path

# Allow running from backend/ directory directly
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OLLAMA_BASE_URL, MODELS, MODELS_FALLBACK, LLM_TIMEOUT_SECONDS
from cache.semantic_cache import cache as _semantic_cache


class ModelRegistry:
    """
    Central client for all Ollama model calls.
    Never call Ollama directly from tools — always go through this registry.
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
        stream: bool = False,
        use_cache: bool = True,
    ) -> str:
        cache_key = f"{model_key}:{system or ''}:{prompt}"
        if use_cache:
            cached = _semantic_cache.get(model_key, cache_key)
            if cached is not None:
                return cached

        model_name = self._resolve_model(model_key)

        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt.copy()

        if system:
            messages.insert(0, {"role": "system", "content": system})

        payload: dict = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "num_ctx": 8192
            }
        }

        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            response = resp.json()["message"]["content"]

        # ── Store in semantic cache ────────────────────────────────────────────
        if use_cache:
            _semantic_cache.put(model_key, cache_key, response)

        return response

    async def generate_stream(
        self,
        model_key: str,
        prompt: str | list[dict],
        system: str = None,
    ):
        model_name = self._resolve_model(model_key)

        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt.copy()

        if system:
            messages.insert(0, {"role": "system", "content": system})

        payload: dict = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "format": "json",
            "options": {
                "num_ctx": 8192
            }
        }

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
                        token = chunk_data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk_data.get("done", False):
                            break
                    except Exception:
                        continue

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

        payload: dict = {
            "model": self._resolve_model("vision"),
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["response"]

    async def health_check(self) -> dict:
        """Return list of locally available Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                return {"status": "ok", "models": resp.json().get("models", [])}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _resolve_model(self, model_key: str) -> str:
        """Return model name string for the given key."""
        if model_key not in self.models:
            raise ValueError(f"Unknown model key: {model_key!r}. "
                             f"Valid keys: {list(self.models.keys())}")
        return self.models[model_key]

    def get_cache_stats(self) -> dict:
        """Return semantic cache statistics."""
        return _semantic_cache.stats()


# ── Singleton — import this from everywhere ──
registry = ModelRegistry()
