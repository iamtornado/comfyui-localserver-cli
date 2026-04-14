# comfyui-localserver-cli

[English](README.en.md) | [中文](README.md)

Small CLI for **locally hosted ComfyUI** (`server.py` / aiohttp), aimed at AI agents (OpenClaw, Cursor, and similar). It wraps the documented HTTP API (for example [`/prompt`](https://docs.comfy.org/development/comfyui-server/comms_routes), [`/queue`](https://docs.comfy.org/development/comfyui-server/comms_routes), [`/history`](https://docs.comfy.org/development/comfyui-server/comms_routes)) and optional WebSocket progress ([message types](https://docs.comfy.org/development/comfyui-server/comms_messages)).

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

The `comfyui-local` command is installed on your PATH.

## Agent-oriented usage

- **Stdout**: one JSON object per invocation (use `--pretty` for indented JSON).
- **Base URL**: set `COMFYUI_BASE_URL` (default `http://127.0.0.1:8188`) or pass `--base-url`.
- **Workflow JSON**: use ComfyUI **Save (API format)**. Provide `--workflow file.json` or pipe JSON on **stdin**.
- **Proxy env vars**: disabled by default to avoid local SOCKS/proxy issues; enable with `--trust-env` when needed.

Examples:

```bash
# Health / VRAM-ish stats
comfyui-local health
comfyui-local health --deep

# Queue a workflow (stdin)
comfyui-local prompt submit < workflow_api.json

# Queue and block until history contains outputs (polls GET /history/{prompt_id})
comfyui-local prompt wait --workflow workflow_api.json --timeout-sec 600

# Same, but connect WebSocket first for earlier completion signal (still uses history for image list)
comfyui-local prompt wait --workflow workflow_api.json --websocket

# Queue inspection / control (see ComfyUI server.py for POST /queue semantics)
comfyui-local queue get
comfyui-local queue clear
comfyui-local queue delete <prompt_id>

comfyui-local interrupt
comfyui-local history --prompt-id <prompt_id>
```

### Exit codes

- `0`: success
- `1`: runtime / execution error (for example history reports `status_str` = `error`)
- `2`: HTTP 4xx from the server (except validation)
- `3`: prompt validation failure (`POST /prompt` returns `node_errors`)
- `4`: HTTP 5xx
- `5`: `prompt wait` timed out before history contained the `prompt_id`
- `130`: interrupted (Ctrl+C)

## Development

```bash
pip install -e ".[dev]"
pytest
```

