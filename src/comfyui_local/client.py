from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx


def default_base_url() -> str:
    return (os.environ.get("COMFYUI_BASE_URL") or "http://127.0.0.1:8188").rstrip("/")


class ComfyUIError(Exception):
    """Base error for ComfyUI CLI."""

    def __init__(self, message: str, *, exit_code: int = 1, detail: Any = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.detail = detail


class ComfyUIHTTPError(ComfyUIError):
    pass


class ComfyUIPromptValidationError(ComfyUIError):
    pass


class ComfyUIClient:
    """Thin synchronous HTTP client for ComfyUI local server routes."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        timeout: float = 300.0,
        transport: Optional[httpx.BaseTransport] = None,
        trust_env: bool = False,
    ):
        self.base_url = (base_url or default_base_url()).rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
            trust_env=trust_env,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ComfyUIClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: Optional[dict[str, Any]] = None,
    ) -> tuple[int, Any]:
        try:
            r = self._client.request(
                method,
                path,
                json=json_body,
                params=params,
            )
        except httpx.RequestError as e:
            raise ComfyUIError(f"connection failed: {e}", exit_code=1, detail=str(e)) from e

        body: Any
        ctype = r.headers.get("content-type", "")
        if "application/json" in ctype and r.content:
            try:
                body = r.json()
            except json.JSONDecodeError:
                body = r.text
        elif r.content:
            try:
                body = r.json()
            except json.JSONDecodeError:
                body = r.text
        else:
            body = None

        return r.status_code, body

    def get_system_stats(self) -> Any:
        code, body = self.request("GET", "/system_stats")
        if code >= 400:
            raise ComfyUIHTTPError(
                f"GET /system_stats failed: HTTP {code}",
                exit_code=2 if code < 500 else 3,
                detail=body,
            )
        return body

    def get_features(self) -> Any:
        code, body = self.request("GET", "/features")
        if code >= 400:
            raise ComfyUIHTTPError(
                f"GET /features failed: HTTP {code}",
                exit_code=2 if code < 500 else 3,
                detail=body,
            )
        return body

    def get_prompt_info(self) -> Any:
        code, body = self.request("GET", "/prompt")
        if code >= 400:
            raise ComfyUIHTTPError(
                f"GET /prompt failed: HTTP {code}",
                exit_code=2 if code < 500 else 3,
                detail=body,
            )
        return body

    def get_queue(self) -> Any:
        code, body = self.request("GET", "/queue")
        if code >= 400:
            raise ComfyUIHTTPError(
                f"GET /queue failed: HTTP {code}",
                exit_code=2 if code < 500 else 3,
                detail=body,
            )
        return body

    def post_queue(self, payload: dict[str, Any]) -> tuple[int, Any]:
        return self.request("POST", "/queue", json_body=payload)

    def post_interrupt(self, payload: Optional[dict[str, Any]] = None) -> tuple[int, Any]:
        return self.request("POST", "/interrupt", json_body=payload or {})

    def get_history(self, prompt_id: Optional[str] = None) -> Any:
        if prompt_id:
            path = f"/history/{prompt_id}"
        else:
            path = "/history"
        code, body = self.request("GET", path)
        if code >= 400:
            raise ComfyUIHTTPError(
                f"GET {path} failed: HTTP {code}",
                exit_code=2 if code < 500 else 3,
                detail=body,
            )
        return body

    def post_prompt(self, payload: dict[str, Any]) -> tuple[int, Any]:
        return self.request("POST", "/prompt", json_body=payload)
