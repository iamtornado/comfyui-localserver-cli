from __future__ import annotations

from comfyui_local.history_util import (
    extract_image_outputs,
    history_completed,
    summarize_history_entry,
    view_url,
)


def test_history_completed() -> None:
    assert not history_completed({}, "abc")
    assert history_completed({"abc": {"outputs": {}}}, "abc")


def test_extract_images_and_view_url() -> None:
    entry = {
        "outputs": {
            "9": {
                "images": [
                    {"filename": "out_00001_.png", "subfolder": "", "type": "output"},
                ]
            }
        }
    }
    imgs = extract_image_outputs(entry)
    assert len(imgs) == 1
    u = view_url("http://127.0.0.1:8188", imgs[0])
    assert u.startswith("http://127.0.0.1:8188/view?")
    assert "filename=out_00001_.png" in u
    summary = summarize_history_entry("http://127.0.0.1:8188", "pid", entry)
    assert summary["prompt_id"] == "pid"
    assert len(summary["view_urls"]) == 1
