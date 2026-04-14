from __future__ import annotations

import json

import httpx
import pytest

from comfyui_local.cli import _post_prompt_and_resolve_id
from comfyui_local.client import ComfyUIClient, ComfyUIPromptValidationError


def test_post_prompt_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "p1", "number": 1.0, "node_errors": {}})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with ComfyUIClient("http://test", transport=transport) as c:
        code, body = c.post_prompt({"prompt": {}, "client_id": "c", "prompt_id": "p1"})
    assert code == 200
    assert isinstance(body, dict)
    assert body.get("prompt_id") == "p1"


def test_post_prompt_validation_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"type": "bad"}, "node_errors": {"1": {}}})

    transport = httpx.MockTransport(handler)
    with ComfyUIClient("http://test", transport=transport) as c:
        with pytest.raises(ComfyUIPromptValidationError):
            _post_prompt_and_resolve_id(c, {"1": {}}, "c", "p", None)


def test_post_queue_clear_body() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/queue":
            captured["body"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(200)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with ComfyUIClient("http://test", transport=transport) as c:
        code, _ = c.post_queue({"clear": True})
    assert code == 200
    assert captured["body"] == {"clear": True}
