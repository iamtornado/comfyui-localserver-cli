from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Optional

import typer

from comfyui_local.client import (
    ComfyUIClient,
    ComfyUIError,
    ComfyUIHTTPError,
    ComfyUIPromptValidationError,
    default_base_url,
)
from comfyui_local.history_util import (
    _history_entry_for_prompt,
    history_completed,
    summarize_history_entry,
)
from comfyui_local.io_util import emit_json, log_verbose, read_workflow_json
from comfyui_local.ws_util import http_to_ws_base, watch_prompt_ws

app = typer.Typer(
    name="comfyui-localserver-cli",
    help="ComfyUI local server CLI for AI agents (JSON on stdout).",
    no_args_is_help=True,
)


@app.callback()
def global_options(
    ctx: typer.Context,
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        help="ComfyUI server URL (default: env COMFYUI_BASE_URL or http://127.0.0.1:8188)",
    ),
    pretty: bool = typer.Option(False, "--pretty", help="Pretty-print JSON on stdout"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Log to stderr"),
    trust_env: bool = typer.Option(
        False,
        "--trust-env/--no-trust-env",
        help="Let HTTP client read proxy/TLS environment variables (disabled by default)",
    ),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["base_url"] = (base_url or default_base_url()).rstrip("/")
    ctx.obj["pretty"] = pretty
    ctx.obj["verbose"] = verbose
    ctx.obj["trust_env"] = trust_env


def _client(ctx: typer.Context, timeout: float = 300.0) -> ComfyUIClient:
    return ComfyUIClient(
        ctx.obj["base_url"],
        timeout=timeout,
        trust_env=bool(ctx.obj.get("trust_env", False)),
    )


def _emit(ctx: typer.Context, data: Any) -> None:
    emit_json(data, pretty=ctx.obj["pretty"])


def _resolved_verbose(ctx: typer.Context, local_verbose: bool) -> bool:
    return bool(ctx.obj.get("verbose", False)) or local_verbose


def _exit(e: ComfyUIError) -> None:
    err_body: dict[str, Any] = {"error": str(e)}
    if e.detail is not None:
        err_body["detail"] = e.detail
    emit_json(err_body, pretty=False)
    raise typer.Exit(e.exit_code)


prompt_app = typer.Typer(help="Queue and run API-format workflows")
app.add_typer(prompt_app, name="prompt")

queue_app = typer.Typer(help="Inspect and manage the execution queue")
app.add_typer(queue_app, name="queue")


@app.command("health")
def health_cmd(
    ctx: typer.Context,
    deep: bool = typer.Option(False, "--deep", help="Include GET /features in addition to /system_stats"),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Pretty-print JSON for this command (compat: supports `health --pretty`)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose logs for this command (compat: supports `health --verbose`)",
    ),
) -> None:
    """GET /system_stats (and optionally /features)."""
    v = _resolved_verbose(ctx, verbose)
    try:
        log_verbose("Running health check", verbose=v)
        with _client(ctx) as c:
            out: dict[str, Any] = {"system_stats": c.get_system_stats()}
            if deep:
                out["features"] = c.get_features()
        emit_json(out, pretty=bool(ctx.obj["pretty"]) or pretty)
    except ComfyUIError as e:
        _exit(e)


@app.command("interrupt")
def interrupt_cmd(
    ctx: typer.Context,
    prompt_id: Optional[str] = typer.Option(
        None,
        "--prompt-id",
        help="If set, interrupt only when this prompt_id is running; otherwise global interrupt",
    ),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Pretty-print JSON for this command (compat: supports `interrupt --pretty`)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose logs for this command (compat: supports `interrupt --verbose`)",
    ),
) -> None:
    """POST /interrupt (optional targeted prompt_id in JSON body)."""
    payload: dict[str, Any] = {}
    if prompt_id:
        payload["prompt_id"] = prompt_id
    v = _resolved_verbose(ctx, verbose)
    try:
        log_verbose(f"POST /interrupt payload={payload}", verbose=v)
        with _client(ctx) as c:
            code, body = c.post_interrupt(payload)
        if code >= 400:
            raise ComfyUIHTTPError(
                f"POST /interrupt failed: HTTP {code}",
                exit_code=2 if code < 500 else 4,
                detail=body,
            )
        emit_json({"ok": True, "http_status": code, "body": body}, pretty=bool(ctx.obj["pretty"]) or pretty)
    except ComfyUIError as e:
        _exit(e)


@queue_app.command("get")
def queue_get(
    ctx: typer.Context,
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Pretty-print JSON for this command (compat: supports `queue get --pretty`)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose logs for this command (compat: supports `queue get --verbose`)",
    ),
) -> None:
    """GET /queue (queue_running, queue_pending)."""
    v = _resolved_verbose(ctx, verbose)
    try:
        log_verbose("GET /queue", verbose=v)
        with _client(ctx) as c:
            emit_json(c.get_queue(), pretty=bool(ctx.obj["pretty"]) or pretty)
    except ComfyUIError as e:
        _exit(e)


@queue_app.command("clear")
def queue_clear(
    ctx: typer.Context,
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Pretty-print JSON for this command (compat: supports `queue clear --pretty`)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose logs for this command (compat: supports `queue clear --verbose`)",
    ),
) -> None:
    """POST /queue with {\"clear\": true} — removes pending items (ComfyUI server.py)."""
    v = _resolved_verbose(ctx, verbose)
    try:
        log_verbose("POST /queue {clear:true}", verbose=v)
        with _client(ctx) as c:
            code, body = c.post_queue({"clear": True})
        if code >= 400:
            raise ComfyUIHTTPError(
                f"POST /queue failed: HTTP {code}",
                exit_code=2 if code < 500 else 4,
                detail=body,
            )
        emit_json({"ok": True, "http_status": code, "body": body}, pretty=bool(ctx.obj["pretty"]) or pretty)
    except ComfyUIError as e:
        _exit(e)


@queue_app.command("delete")
def queue_delete(
    ctx: typer.Context,
    prompt_id: list[str] = typer.Argument(..., help="One or more prompt_id values to remove from pending queue"),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Pretty-print JSON for this command (compat: supports `queue delete --pretty`)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose logs for this command (compat: supports `queue delete --verbose`)",
    ),
) -> None:
    """POST /queue with {\"delete\": [prompt_id, ...]}."""
    v = _resolved_verbose(ctx, verbose)
    try:
        log_verbose(f"POST /queue delete={list(prompt_id)}", verbose=v)
        with _client(ctx) as c:
            code, body = c.post_queue({"delete": list(prompt_id)})
        if code >= 400:
            raise ComfyUIHTTPError(
                f"POST /queue failed: HTTP {code}",
                exit_code=2 if code < 500 else 4,
                detail=body,
            )
        emit_json({"ok": True, "http_status": code, "body": body}, pretty=bool(ctx.obj["pretty"]) or pretty)
    except ComfyUIError as e:
        _exit(e)


@app.command("history")
def history_cmd(
    ctx: typer.Context,
    prompt_id: Optional[str] = typer.Option(
        None,
        "--prompt-id",
        help="GET /history/{prompt_id}; omit for GET /history",
    ),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Pretty-print JSON for this command (compat: supports `history --pretty`)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose logs for this command (compat: supports `history --verbose`)",
    ),
) -> None:
    """GET /history or /history/{prompt_id}."""
    v = _resolved_verbose(ctx, verbose)
    try:
        log_verbose(f"GET /history prompt_id={prompt_id}", verbose=v)
        with _client(ctx) as c:
            emit_json(c.get_history(prompt_id), pretty=bool(ctx.obj["pretty"]) or pretty)
    except ComfyUIError as e:
        _exit(e)


def _post_prompt_and_resolve_id(
    c: ComfyUIClient,
    workflow: dict[str, Any],
    client_id: str,
    prompt_id: str,
    extra_data: Optional[dict[str, Any]],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": workflow,
        "client_id": client_id,
        "prompt_id": prompt_id,
    }
    if extra_data is not None:
        payload["extra_data"] = extra_data
    code, body = c.post_prompt(payload)
    if code == 200 and isinstance(body, dict):
        return body
    if code == 400 and isinstance(body, dict):
        raise ComfyUIPromptValidationError(
            "prompt validation failed",
            exit_code=3,
            detail=body,
        )
    raise ComfyUIHTTPError(
        f"POST /prompt failed: HTTP {code}",
        exit_code=2 if code < 500 else 4,
        detail=body,
    )


@prompt_app.command("submit")
def prompt_submit(
    ctx: typer.Context,
    workflow_path: Optional[Path] = typer.Option(
        None,
        "--workflow",
        "-w",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Path to API-format workflow JSON; else read stdin",
    ),
    client_id: Optional[str] = typer.Option(
        None,
        "--client-id",
        help="WebSocket client id (default: random UUID)",
    ),
    prompt_id: Optional[str] = typer.Option(
        None,
        "--prompt-id",
        help="Explicit prompt_id (default: random UUID)",
    ),
    raw: bool = typer.Option(False, "--raw", help="Include full POST /prompt response fields only"),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Pretty-print JSON for this command (compat: supports `prompt submit --pretty`)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose logs for this command (compat: supports `prompt submit --verbose`)",
    ),
) -> None:
    """POST /prompt — queue a workflow; returns prompt_id and queue number."""
    cid = client_id or str(uuid.uuid4())
    pid = prompt_id or str(uuid.uuid4())
    v = _resolved_verbose(ctx, verbose)
    try:
        wf = read_workflow_json(workflow_path)
        with _client(ctx) as c:
            body = _post_prompt_and_resolve_id(c, wf, cid, pid, None)
        log_verbose(f"client_id={cid} prompt_id={pid}", verbose=v)
        if raw:
            emit_json(body, pretty=bool(ctx.obj["pretty"]) or pretty)
        else:
            emit_json(
                {
                    "prompt_id": body.get("prompt_id", pid),
                    "number": body.get("number"),
                    "client_id": cid,
                    "node_errors": body.get("node_errors"),
                },
                pretty=bool(ctx.obj["pretty"]) or pretty,
            )
    except ComfyUIError as e:
        _exit(e)
    except typer.BadParameter as e:
        emit_json({"error": str(e)}, pretty=False)
        raise typer.Exit(1)


@prompt_app.command("wait")
def prompt_wait(
    ctx: typer.Context,
    workflow_path: Optional[Path] = typer.Option(
        None,
        "--workflow",
        "-w",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Path to API-format workflow JSON; else read stdin",
    ),
    client_id: Optional[str] = typer.Option(None, "--client-id"),
    prompt_id: Optional[str] = typer.Option(None, "--prompt-id"),
    timeout_sec: float = typer.Option(600.0, "--timeout-sec"),
    poll_interval_sec: float = typer.Option(0.5, "--poll-interval-sec"),
    use_websocket: bool = typer.Option(
        False,
        "--websocket/--no-websocket",
        help="Use WebSocket for earlier completion detection (still polls /history for outputs)",
    ),
    raw_history: bool = typer.Option(False, "--raw-history", help="Include full history entry under raw_history"),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        help="Pretty-print JSON for this command (compat: supports `prompt wait --pretty`)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose logs for this command (compat: supports `prompt wait --verbose`)",
    ),
) -> None:
    """POST /prompt, then poll GET /history/{prompt_id} until done or timeout."""
    cid = client_id or str(uuid.uuid4())
    pid = prompt_id or str(uuid.uuid4())
    base = ctx.obj["base_url"]
    v = _resolved_verbose(ctx, verbose)

    try:
        wf = read_workflow_json(workflow_path)
    except typer.BadParameter as e:
        emit_json({"error": str(e)}, pretty=False)
        raise typer.Exit(1)

    ws_outcome: Optional[str] = None
    ws_last: Optional[dict[str, Any]] = None
    submit_body: Optional[dict[str, Any]] = None
    deadline = time.monotonic() + timeout_sec

    def do_submit() -> None:
        nonlocal submit_body
        with _client(ctx, timeout=timeout_sec) as c:
            submit_body = _post_prompt_and_resolve_id(c, wf, cid, pid, None)

    try:
        if use_websocket:
            ws_outcome, ws_last = watch_prompt_ws(
                http_to_ws_base(base),
                cid,
                pid,
                deadline_monotonic=deadline,
                verbose=v,
                after_connect=do_submit,
            )
        else:
            do_submit()

        if submit_body is None:
            raise ComfyUIError("internal: submit did not run", exit_code=1)

        hist: Any = {}
        while time.monotonic() < deadline:
            if history_completed(hist, pid):
                break
            time.sleep(poll_interval_sec)
            with _client(ctx, timeout=min(60.0, max(1.0, deadline - time.monotonic()))) as c:
                hist = c.get_history(pid)

        entry = _history_entry_for_prompt(hist, pid)
        timed_out = entry is None and time.monotonic() >= deadline

        result: dict[str, Any] = {
            "prompt_id": pid,
            "client_id": cid,
            "submit": {
                "number": submit_body.get("number"),
                "node_errors": submit_body.get("node_errors"),
            },
            "ws": {"outcome": ws_outcome, "last_event": ws_last} if use_websocket else None,
            "timed_out": timed_out,
        }

        if entry:
            result["result"] = summarize_history_entry(base, pid, entry)
            if raw_history:
                result["raw_history"] = entry
        else:
            result["result"] = None
            with _client(ctx) as c:
                result["queue_snapshot"] = c.get_queue()

        emit_json(result, pretty=bool(ctx.obj["pretty"]) or pretty)

        if timed_out:
            raise typer.Exit(5)
        if ws_outcome == "error":
            raise typer.Exit(1)
        st = entry.get("status") if entry and isinstance(entry, dict) else None
        if isinstance(st, dict) and st.get("status_str") == "error":
            raise typer.Exit(1)

    except ComfyUIError as e:
        _exit(e)


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        emit_json({"error": "interrupted"}, pretty=False)
        raise typer.Exit(130)


if __name__ == "__main__":
    main()
