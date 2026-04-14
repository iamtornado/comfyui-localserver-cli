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

## Recent test results

The following is from a real local run:

```bash
comfyui-local health --pretty
```

```json
{
  "system_stats": {
    "system": {
      "os": "linux",
      "ram_total": 151697399808,
      "ram_free": 144025849856,
      "comfyui_version": "0.18.1",
      "required_frontend_version": "1.42.8",
      "installed_templates_version": "0.9.44",
      "required_templates_version": "0.9.44",
      "python_version": "3.14.3 (main, Feb  3 2026, 15:32:20) [GCC 12.3.0]",
      "pytorch_version": "2.11.0+cu130",
      "embedded_python": false,
      "argv": [
        "main.py",
        "--listen",
        "0.0.0.0",
        "--enable-manager"
      ]
    },
    "devices": [
      {
        "name": "cuda:0 Quadro RTX 5000 : cudaMallocAsync",
        "type": "cuda",
        "index": 0,
        "vram_total": 16700604416,
        "vram_free": 16572809216,
        "torch_vram_total": 0,
        "torch_vram_free": 0
      }
    ]
  }
}
```

```bash
pytest -q
```

- `7 passed`

## Development

```bash
pip install -e ".[dev]"
pytest
```

