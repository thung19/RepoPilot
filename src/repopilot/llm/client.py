"""Minimal LLM client interface and an Ollama implementation.

The interface is deliberately small so another provider can be added
as one more class. Clients return raw text: parsing and validation
happen elsewhere so failures there can be reported precisely.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Protocol

from pydantic import BaseModel

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"

# Ollama's default context window is small and it silently drops input
# that does not fit, so the window is always set explicitly.
DEFAULT_NUM_CTX = 32_768
DEFAULT_MAX_OUTPUT_TOKENS = 4_096

# Conservative characters-per-token ratio for the preflight size check.
CHARS_PER_TOKEN = 3


class LLMError(RuntimeError):
    """The model could not produce a usable response."""


class LLMResponse(BaseModel):
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_seconds: float


class LLMClient(Protocol):
    # Largest system + user prompt, in characters, the client accepts.
    max_prompt_chars: int

    def generate(
        self,
        system: str,
        user: str,
        schema: dict,
    ) -> LLMResponse:
        """Return a response whose text should match `schema`."""
        ...


class OllamaClient:
    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        host: str | None = None,
        num_ctx: int = DEFAULT_NUM_CTX,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        timeout_seconds: float = 600,
    ):
        self.model = model
        self.host = (
            host or os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST
        ).rstrip("/")
        if "://" not in self.host:
            self.host = f"http://{self.host}"
        self.num_ctx = num_ctx
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds

    @property
    def max_prompt_chars(self) -> int:
        # The `format` schema becomes a decoding grammar and does not
        # use context tokens, so only the messages are counted.
        return (self.num_ctx - self.max_output_tokens) * CHARS_PER_TOKEN

    def check_fits(self, system: str, user: str) -> None:
        prompt_chars = len(system) + len(user)

        if prompt_chars > self.max_prompt_chars:
            raise LLMError(
                f"Prompt is {prompt_chars} characters but at most "
                f"{self.max_prompt_chars} fit in num_ctx={self.num_ctx} "
                f"after reserving {self.max_output_tokens} tokens for "
                "output. Reduce the evidence or raise num_ctx."
            )

    def generate(
        self,
        system: str,
        user: str,
        schema: dict,
    ) -> LLMResponse:
        self.check_fits(system, user)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            # Constrains decoding so the output matches the schema.
            "format": schema,
            "options": {
                "num_ctx": self.num_ctx,
                "num_predict": self.max_output_tokens,
                "temperature": 0,
                "seed": 0,
            },
        }

        request = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        start = time.monotonic()

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                body = json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            if error.code == 404:
                raise LLMError(
                    f"Model '{self.model}' is not available in Ollama. "
                    f"Run: ollama pull {self.model}"
                ) from error
            raise LLMError(
                f"Ollama returned HTTP {error.code}: {detail}"
            ) from error

        except (urllib.error.URLError, TimeoutError) as error:
            raise LLMError(
                f"Cannot reach Ollama at {self.host} ({error}). "
                "Is it running? Start it with: ollama serve"
            ) from error

        duration = time.monotonic() - start

        if body.get("done_reason") == "length":
            raise LLMError(
                "Model output was cut off at "
                f"{self.max_output_tokens} tokens; the JSON is incomplete."
            )

        input_tokens = body.get("prompt_eval_count")
        if input_tokens is not None and input_tokens >= self.num_ctx:
            raise LLMError(
                "Prompt filled the whole context window and was "
                "truncated by Ollama."
            )

        return LLMResponse(
            text=body.get("message", {}).get("content", ""),
            model=body.get("model", self.model),
            input_tokens=input_tokens,
            output_tokens=body.get("eval_count"),
            duration_seconds=duration,
        )
