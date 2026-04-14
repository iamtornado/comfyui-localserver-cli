---
name: comfyui-local-cli
description: Run local ComfyUI workflows through the comfyui-local CLI, including prompt injection, seed/filename overrides, submit/wait patterns, and result parsing. Use when users ask to run ComfyUI API JSON workflows, change prompts without editing source files, or automate image generation for AI agents.
---

# comfyui-local-cli

## When to use

Use this skill when the task mentions:

- `comfyui-local` commands
- local ComfyUI workflow execution
- changing prompt/seed/output filename at runtime
- `prompt submit` / `prompt wait`
- parsing generated image names or `view_urls`

## Assumptions

- ComfyUI server is running locally (default `http://127.0.0.1:8188`)
- Workflow is API-format JSON
- CLI is available as `comfyui-local`

## Core workflow

1. Identify modifiable node paths in workflow JSON (for example text, seed, filename prefix).
2. Use `jq` to patch JSON on stdin (avoid mutating source files unless requested).
3. Pipe to `comfyui-local prompt wait` for end-to-end execution.
4. Return key fields: `prompt_id`, `status`, `images[].filename`, `view_urls[]`.

## Command patterns

### Health check

```bash
comfyui-local health --pretty
```

### Run workflow with prompt override

```bash
PROMPT='A cinematic portrait, warm tones, ultra detailed'
jq --arg p "$PROMPT" '.["57:27"].inputs.text = $p' workflow.json \
  | comfyui-local prompt wait --pretty --timeout-sec 120
```

### Override prompt + seed + output filename prefix

```bash
PROMPT='A cinematic portrait, warm tones, ultra detailed'
SEED=123456789
OUT='my_custom_name'

jq --arg p "$PROMPT" --argjson s "$SEED" --arg o "$OUT" \
  '.["57:27"].inputs.text = $p
   | .["57:3"].inputs.seed = $s
   | .["9"].inputs.filename_prefix = $o' \
  workflow.json \
  | comfyui-local prompt wait --pretty --timeout-sec 120
```

### Submit only (non-blocking)

```bash
jq --arg p "$PROMPT" '.["57:27"].inputs.text = $p' workflow.json \
  | comfyui-local prompt submit --pretty
```

### Submit first, check progress later

```bash
PROMPT='A cinematic portrait, warm tones, ultra detailed'

# 1) Submit without waiting, capture prompt_id
PROMPT_ID=$(
  jq --arg p "$PROMPT" '.["57:27"].inputs.text = $p' workflow.json \
    | comfyui-local prompt submit \
    | jq -r '.prompt_id'
)

echo "prompt_id=$PROMPT_ID"

# 2) Check current queue status (running/pending)
comfyui-local queue get --pretty

# 3) Query this prompt's history/result when needed
comfyui-local history --prompt-id "$PROMPT_ID" --pretty
```

## Output interpretation

- Success signal:
  - `timed_out: false`
  - `result.status: "success"`
  - at least one `result.images[]`
- Use `result.view_urls[]` for direct image preview/download route.
- Saved filename comes from `SaveImage.inputs.filename_prefix` plus ComfyUI counter suffix (for example `_00001_.png`).

## Troubleshooting

- `No such option: --pretty`:
  - Use latest CLI in this repo; `prompt wait --pretty` and `prompt submit --pretty` are supported.
- SOCKS/proxy errors:
  - CLI defaults to not reading proxy env vars.
  - Enable only if needed: `--trust-env`.
- Timeout:
  - Increase `--timeout-sec` and re-run.
  - Check `queue get` and `history --prompt-id <id>`.

## Agent response checklist

- Include the exact command(s) the user can copy.
- Mention which JSON paths were overridden.
- Summarize run result fields (`status`, `filename`, `view_url`).
- If failed, include actionable next command (health/queue/history).
