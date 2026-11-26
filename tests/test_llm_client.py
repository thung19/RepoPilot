import io
import json
import urllib.error

import pytest

from repopilot.llm import client as client_module
from repopilot.llm.client import LLMError, OllamaClient


class FakeHTTPResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode("utf-8")

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def ok_body(**overrides):
    body = {
        "model": "llama3.1:8b",
        "message": {"role": "assistant", "content": '{"a": 1}'},
        "done_reason": "stop",
        "prompt_eval_count": 1200,
        "eval_count": 300,
    }
    body.update(overrides)
    return body


@pytest.fixture
def capture(monkeypatch):
    """Replace urlopen; record requests and return a configurable body."""
    state = {"requests": [], "body": ok_body(), "error": None}

    def fake_urlopen(request, timeout):
        state["requests"].append(json.loads(request.data))
        state["url"] = request.full_url
        if state["error"] is not None:
            raise state["error"]
        return FakeHTTPResponse(state["body"])

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    return state


def test_request_payload(capture):
    client = OllamaClient(model="m", num_ctx=8192, max_output_tokens=1000)
    schema = {"type": "object"}

    client.generate("sys", "user", schema)

    payload = capture["requests"][0]
    assert capture["url"] == "http://localhost:11434/api/chat"
    assert payload["model"] == "m"
    assert payload["stream"] is False
    assert payload["format"] == schema
    assert payload["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "user"},
    ]
    assert payload["options"] == {
        "num_ctx": 8192,
        "num_predict": 1000,
        "temperature": 0,
        "seed": 0,
    }


def test_response_fields(capture):
    response = OllamaClient().generate("s", "u", {})

    assert response.text == '{"a": 1}'
    assert response.model == "llama3.1:8b"
    assert response.input_tokens == 1200
    assert response.output_tokens == 300


def test_host_from_environment(capture, monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:9999")

    OllamaClient().generate("s", "u", {})

    assert capture["url"] == "http://127.0.0.1:9999/api/chat"


def test_max_prompt_chars():
    client = OllamaClient(num_ctx=1000, max_output_tokens=500)

    # 500 tokens left for the prompt, 3 characters per token.
    assert client.max_prompt_chars == 1500


def test_prompt_too_large_is_rejected_before_request(capture):
    client = OllamaClient(num_ctx=1000, max_output_tokens=500)

    with pytest.raises(LLMError, match="num_ctx"):
        client.generate("x" * 1500, "u", {})

    assert capture["requests"] == []


def test_truncated_output(capture):
    capture["body"] = ok_body(done_reason="length")

    with pytest.raises(LLMError, match="cut off"):
        OllamaClient().generate("s", "u", {})


def test_truncated_prompt(capture):
    capture["body"] = ok_body(prompt_eval_count=32_768)

    with pytest.raises(LLMError, match="truncated"):
        OllamaClient(num_ctx=32_768).generate("s", "u", {})


def test_model_not_found(capture):
    capture["error"] = urllib.error.HTTPError(
        "url", 404, "Not Found", {}, io.BytesIO(b"model not found")
    )

    with pytest.raises(LLMError, match="ollama pull missing"):
        OllamaClient(model="missing").generate("s", "u", {})


def test_server_unreachable(capture):
    capture["error"] = urllib.error.URLError("Connection refused")

    with pytest.raises(LLMError, match="ollama serve"):
        OllamaClient().generate("s", "u", {})
