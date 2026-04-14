# comfyui-localserver-cli

[中文](README.md) | [English](README.en.md)

这是一个面向 **本地部署 ComfyUI**（`server.py` / aiohttp）的 CLI，主要给 AI Agent（如 OpenClaw、Cursor 等）调用。它封装了官方文档中的 HTTP API（例如 [`/prompt`](https://docs.comfy.org/development/comfyui-server/comms_routes)、[`/queue`](https://docs.comfy.org/development/comfyui-server/comms_routes)、[`/history`](https://docs.comfy.org/development/comfyui-server/comms_routes)）以及可选的 WebSocket 进度事件（[message types](https://docs.comfy.org/development/comfyui-server/comms_messages)）。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

安装完成后可直接使用命令 `comfyui-local`。

## 面向 Agent 的使用方式

- **标准输出**：每次调用默认输出一个 JSON 对象（可加 `--pretty` 美化）。
- **服务地址**：通过环境变量 `COMFYUI_BASE_URL`（默认 `http://127.0.0.1:8188`）或参数 `--base-url` 指定。
- **工作流输入**：使用 ComfyUI 的 **Save (API format)** 导出 JSON；可通过 `--workflow file.json` 或 stdin 传入。
- **代理环境变量**：默认不读取（避免本地 SOCKS/代理干扰）；需要时可加 `--trust-env` 开启。

示例：

```bash
# 健康检查 / 系统信息
comfyui-local health
comfyui-local health --deep

# 提交工作流（从 stdin 读取）
comfyui-local prompt submit < workflow_api.json

# 提交并阻塞等待完成（轮询 GET /history/{prompt_id}）
comfyui-local prompt wait --workflow workflow_api.json --timeout-sec 600

# 先连 WebSocket 以更早感知完成（仍用 history 提取产物）
comfyui-local prompt wait --workflow workflow_api.json --websocket

# 队列查看与控制（POST /queue 语义以 ComfyUI server.py 为准）
comfyui-local queue get
comfyui-local queue clear
comfyui-local queue delete <prompt_id>

comfyui-local interrupt
comfyui-local history --prompt-id <prompt_id>
```

### 退出码

- `0`：成功
- `1`：运行时/执行错误（例如 history 中 `status_str` 为 `error`）
- `2`：服务端返回 HTTP 4xx（校验错误除外）
- `3`：prompt 校验失败（`POST /prompt` 返回 `node_errors`）
- `4`：服务端返回 HTTP 5xx
- `5`：`prompt wait` 超时（在超时前未在 history 看到对应 `prompt_id`）
- `130`：被中断（Ctrl+C）

## 开发

```bash
pip install -e ".[dev]"
pytest
```

