from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote


def _history_entry_for_prompt(history_response: Any, prompt_id: str) -> Optional[dict[str, Any]]:
    if not isinstance(history_response, dict):
        return None
    entry = history_response.get(prompt_id)
    if isinstance(entry, dict):
        return entry
    return None


def history_completed(history_response: Any, prompt_id: str) -> bool:
    return _history_entry_for_prompt(history_response, prompt_id) is not None


def extract_status(entry: dict[str, Any]) -> Optional[str]:
    status = entry.get("status")
    if isinstance(status, dict):
        s = status.get("status_str")
        if isinstance(s, str):
            return s
    return None


def extract_image_outputs(entry: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    outputs = entry.get("outputs")
    if not isinstance(outputs, dict):
        return out
    for node_id, node_out in outputs.items():
        if not isinstance(node_out, dict):
            continue
        images = node_out.get("images")
        if not isinstance(images, list):
            continue
        for img in images:
            if isinstance(img, dict) and img.get("filename"):
                out.append(
                    {
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder") or "",
                        "type": img.get("type") or "output",
                        "node_id": str(node_id),
                    }
                )
    return out


def view_url(base_url: str, ref: dict[str, Any]) -> str:
    base = base_url.rstrip("/")
    filename = ref["filename"]
    typ = ref.get("type") or "output"
    subfolder = ref.get("subfolder") or ""
    q = f"filename={quote(filename)}&type={quote(typ)}"
    if subfolder:
        q += f"&subfolder={quote(subfolder)}"
    return f"{base}/view?{q}"


def summarize_history_entry(
    base_url: str,
    prompt_id: str,
    entry: dict[str, Any],
) -> dict[str, Any]:
    images = extract_image_outputs(entry)
    return {
        "prompt_id": prompt_id,
        "status": extract_status(entry),
        "images": images,
        "view_urls": [view_url(base_url, i) for i in images],
    }
