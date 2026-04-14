from __future__ import annotations

import json
from unittest.mock import patch

import httpx
from typer.testing import CliRunner

from comfyui_local.client import ComfyUIClient


def test_prompt_wait_polls_until_history_present() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "abc", "number": 1.0, "node_errors": {}})
        if request.method == "GET" and request.url.path == "/history/abc":
            calls["n"] += 1
            if calls["n"] < 3:
                return httpx.Response(200, json={})
            return httpx.Response(
                200,
                json={
                    "abc": {
                        "outputs": {
                            "9": {
                                "images": [
                                    {
                                        "filename": "x.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                },
            )
        if request.method == "GET" and request.url.path == "/queue":
            return httpx.Response(200, json={"queue_running": [], "queue_pending": []})
        return httpx.Response(404, text="unexpected " + request.url.path)

    transport = httpx.MockTransport(handler)

    def mock_client(ctx, timeout: float = 300.0):
        return ComfyUIClient(ctx.obj["base_url"], timeout=timeout, transport=transport)

    runner = CliRunner()
    wf = json.dumps({"1": {"class_type": "Stub"}})
    with patch("comfyui_local.cli._client", mock_client):
        result = runner.invoke(
            __import__("comfyui_local.cli", fromlist=["app"]).app,
            [
                "--base-url",
                "http://test",
                "prompt",
                "wait",
                "--prompt-id",
                "abc",
                "--timeout-sec",
                "5",
                "--poll-interval-sec",
                "0.01",
            ],
            input=wf,
        )
    assert result.exit_code == 0, result.stdout
    out = json.loads(result.stdout)
    assert out["prompt_id"]
    assert out["result"] is not None
    assert out["result"]["images"][0]["filename"] == "x.png"
    assert out["timed_out"] is False


def test_prompt_wait_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "slow", "number": 1.0, "node_errors": {}})
        if request.method == "GET" and request.url.path == "/history/slow":
            return httpx.Response(200, json={})
        if request.method == "GET" and request.url.path == "/queue":
            return httpx.Response(200, json={"queue_running": [], "queue_pending": []})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    def mock_client(ctx, timeout: float = 300.0):
        return ComfyUIClient(ctx.obj["base_url"], timeout=timeout, transport=transport)

    runner = CliRunner()
    wf = json.dumps({"1": {"class_type": "Stub"}})
    with patch("comfyui_local.cli._client", mock_client):
        result = runner.invoke(
            __import__("comfyui_local.cli", fromlist=["app"]).app,
            [
                "--base-url",
                "http://test",
                "prompt",
                "wait",
                "--prompt-id",
                "slow",
                "--timeout-sec",
                "0.15",
                "--poll-interval-sec",
                "0.05",
            ],
            input=wf,
        )
    assert result.exit_code == 5
    out = json.loads(result.stdout)
    assert out["timed_out"] is True
    assert out["result"] is None
