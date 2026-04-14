# comfyui-localserver-cli

[中文](README.md) | [English](README.en.md)

这是一个面向 **本地部署 ComfyUI**（`server.py` / aiohttp）的 CLI，主要给 AI Agent（如 OpenClaw、Cursor 等）调用。它封装了官方文档中的 HTTP API（例如 `[/prompt](https://docs.comfy.org/development/comfyui-server/comms_routes)`、`[/queue](https://docs.comfy.org/development/comfyui-server/comms_routes)`、`[/history](https://docs.comfy.org/development/comfyui-server/comms_routes)`）以及可选的 WebSocket 进度事件（[message types](https://docs.comfy.org/development/comfyui-server/comms_messages)）。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

安装完成后可直接使用命令 `comfyui-localserver-cli`。

## 面向 Agent 的使用方式

- **标准输出**：每次调用默认输出一个 JSON 对象（可加 `--pretty` 美化）。
- **服务地址**：通过环境变量 `COMFYUI_BASE_URL`（默认 `http://127.0.0.1:8188`）或参数 `--base-url` 指定。
- **工作流输入**：使用 ComfyUI 的 **Save (API format)** 导出 JSON；可通过 `--workflow file.json` 或 stdin 传入。
- **代理环境变量**：默认不读取（避免本地 SOCKS/代理干扰）；需要时可加 `--trust-env` 开启。

示例：

```bash
# 健康检查 / 系统信息
comfyui-localserver-cli health
comfyui-localserver-cli health --deep

# 提交工作流（从 stdin 读取）
comfyui-localserver-cli prompt submit < workflow_api.json

# 提交并阻塞等待完成（轮询 GET /history/{prompt_id}）
comfyui-localserver-cli prompt wait --workflow workflow_api.json --timeout-sec 600

# 先连 WebSocket 以更早感知完成（仍用 history 提取产物）
comfyui-localserver-cli prompt wait --workflow workflow_api.json --websocket

# 队列查看与控制（POST /queue 语义以 ComfyUI server.py 为准）
comfyui-localserver-cli queue get
comfyui-localserver-cli queue clear
comfyui-localserver-cli queue delete <prompt_id>

comfyui-localserver-cli interrupt
comfyui-localserver-cli history --prompt-id <prompt_id>
```

### 退出码

- `0`：成功
- `1`：运行时/执行错误（例如 history 中 `status_str` 为 `error`）
- `2`：服务端返回 HTTP 4xx（校验错误除外）
- `3`：prompt 校验失败（`POST /prompt` 返回 `node_errors`）
- `4`：服务端返回 HTTP 5xx
- `5`：`prompt wait` 超时（在超时前未在 history 看到对应 `prompt_id`）
- `130`：被中断（Ctrl+C）

## 最近测试结果

以下为本地实际运行结果：

```bash
comfyui-localserver-cli health --pretty
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

## 开发

```bash
pip install -e ".[dev]"
pytest
```

