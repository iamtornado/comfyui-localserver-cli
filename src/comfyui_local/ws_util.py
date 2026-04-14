from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from comfyui_local.io_util import log_verbose


def http_to_ws_base(http_base: str) -> str:
    u = urlparse(http_base)
    scheme = "wss" if u.scheme == "https" else "ws"
    netloc = u.netloc or u.path
    return f"{scheme}://{netloc}"


def watch_prompt_ws(
    ws_base: str,
    client_id: str,
    prompt_id: str,
    *,
    deadline_monotonic: float,
    verbose: bool,
    after_connect: Callable[[], None],
) -> tuple[str, Optional[dict[str, Any]]]:
    """
    Connect to /ws?clientId=, invoke after_connect() (typically POST /prompt), then
    wait for execution_success or execution_error for prompt_id.
    Returns (outcome, last_event) where outcome is success|error|timeout.
    """
    try:
        import websocket  # type: ignore[import-untyped]
    except ImportError as e:
        raise RuntimeError("websocket-client is required for --websocket") from e

    url = f"{ws_base.rstrip('/')}/ws?clientId={client_id}"
    log_verbose(f"WebSocket: {url}", verbose=verbose)

    inbound: queue.Queue[tuple[str, Any]] = queue.Queue()
    done = threading.Event()

    def on_message(ws: Any, message: str | bytes) -> None:
        if isinstance(message, bytes):
            return
        try:
            msg = json.loads(message)
        except json.JSONDecodeError:
            return
        inbound.put(("json", msg))
        mtype = msg.get("type")
        data = msg.get("data") or {}
        if mtype == "execution_success" and data.get("prompt_id") == prompt_id:
            done.set()
        if mtype == "execution_error" and data.get("prompt_id") == prompt_id:
            done.set()

    def on_error(ws: Any, error: Exception) -> None:
        inbound.put(("error", error))

    def run() -> None:
        ws = websocket.WebSocketApp(
            url,
            on_message=on_message,
            on_error=on_error,
        )
        ws.run_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    time.sleep(0.25)
    after_connect()

    deadline = deadline_monotonic
    last: Optional[dict[str, Any]] = None
    while time.monotonic() < deadline and not done.is_set():
        try:
            kind, payload = inbound.get(timeout=0.2)
        except queue.Empty:
            continue
        if kind == "json" and isinstance(payload, dict):
            last = payload
        elif kind == "error":
            break

    outcome = "timeout"
    if last:
        if last.get("type") == "execution_success" and (last.get("data") or {}).get("prompt_id") == prompt_id:
            outcome = "success"
        elif last.get("type") == "execution_error" and (last.get("data") or {}).get("prompt_id") == prompt_id:
            outcome = "error"

    if done.is_set() and outcome == "timeout" and last:
        if last.get("type") == "execution_success":
            outcome = "success"
        elif last.get("type") == "execution_error":
            outcome = "error"

    return outcome, last
