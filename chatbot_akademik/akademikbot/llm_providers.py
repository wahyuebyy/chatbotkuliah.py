"""
llm_providers.py  -  Adaptor tiga penyedia LLM: Claude (Anthropic), GPT (OpenAI), Gemini (Google).

PENANGGUNG JAWAB: Anggota 3 (LLM & Anti-Halusinasi)

Semuanya memakai REST + urllib bawaan Python (tanpa SDK/dependensi). Satu antarmuka:
    provider.generate(system, pesan) -> str     # pesan = [{"role": "user"|"assistant", "content": ...}]

`transport` bisa disuntik (fungsi pengganti HTTP) supaya semua adaptor teruji tanpa internet.
API key hanya dikirim lewat header dan tidak pernah dimasukkan ke pesan error / log.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable, Optional

from .config import (
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_MODEL_GEMINI,
    LLM_MODEL_GPT,
    LLM_TIMEOUT_DETIK,
)

Transport = Callable[[str, dict, dict, float], dict]   # (url, header, body, timeout) -> JSON


class ProviderError(RuntimeError):
    """Panggilan ke penyedia LLM gagal (jaringan, kuota, respons kosong/diblokir)."""


def http_post_json(url: str, headers: dict, body: dict, timeout: float) -> dict:
    """POST JSON dengan urllib. Isi error server sengaja tidak disertakan (bisa memuat data sensitif)."""
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError(f"jaringan: {type(exc).__name__}") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProviderError("respons bukan JSON") from None


class Provider:
    nama = "dasar"            # kunci di LLM_RUTE: claude | gpt | gemini
    ENV_KEY: tuple[str, ...] = ()

    def __init__(self, api_key: Optional[str] = None, model: str = "",
                 transport: Optional[Transport] = None):
        self.api_key = api_key if api_key is not None else self._kunci_env()
        self.model = model
        self.transport: Transport = transport or http_post_json

    @classmethod
    def _kunci_env(cls) -> Optional[str]:
        return next((os.environ[k] for k in cls.ENV_KEY if os.environ.get(k)), None)

    @property
    def tersedia(self) -> bool:
        return bool(self.api_key)

    def generate(self, system: str, pesan: list[dict[str, str]], max_tokens: Optional[int] = None) -> str:
        if not self.tersedia:
            raise ProviderError(f"API key {self.nama} belum diatur")
        return self._generate(system, pesan, max_tokens or LLM_MAX_TOKENS).strip()

    def _generate(self, system: str, pesan: list[dict[str, str]],
                  max_tokens: int = LLM_MAX_TOKENS) -> str:  # pragma: no cover
        raise NotImplementedError


class ClaudeProvider(Provider):
    nama = "claude"
    ENV_KEY = ("ANTHROPIC_API_KEY",)
    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key=None, model: str = LLM_MODEL, transport=None):
        super().__init__(api_key, model, transport)

    def _generate(self, system, pesan, max_tokens=LLM_MAX_TOKENS):
        d = self.transport(self.URL,
                           {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                           {"model": self.model, "max_tokens": max_tokens,
                            "system": system, "messages": pesan}, LLM_TIMEOUT_DETIK)
        return "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")


class GPTProvider(Provider):
    nama = "gpt"
    ENV_KEY = ("OPENAI_API_KEY",)
    URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key=None, model: str = LLM_MODEL_GPT, transport=None):
        super().__init__(api_key, model, transport)

    def _generate(self, system, pesan, max_tokens=LLM_MAX_TOKENS):
        d = self.transport(self.URL, {"Authorization": f"Bearer {self.api_key}"},
                           {"model": self.model, "max_completion_tokens": max_tokens,
                            "messages": [{"role": "system", "content": system}, *pesan]},
                           LLM_TIMEOUT_DETIK)
        try:
            return d["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise ProviderError("respons GPT tidak berisi teks") from None


class GeminiProvider(Provider):
    nama = "gemini"
    ENV_KEY = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key=None, model: str = LLM_MODEL_GEMINI, transport=None):
        super().__init__(api_key, model, transport)

    def _generate(self, system, pesan, max_tokens=LLM_MAX_TOKENS):
        isi = [{"role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}]} for m in pesan]
        d = self.transport(self.URL.format(model=self.model), {"x-goog-api-key": self.api_key},
                           {"systemInstruction": {"parts": [{"text": system}]}, "contents": isi,
                            "generationConfig": {"maxOutputTokens": max_tokens}},
                           LLM_TIMEOUT_DETIK)
        try:
            return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError, TypeError):
            raise ProviderError("respons Gemini kosong/diblokir") from None


SEMUA_PROVIDER = {"claude": ClaudeProvider, "gpt": GPTProvider, "gemini": GeminiProvider}
