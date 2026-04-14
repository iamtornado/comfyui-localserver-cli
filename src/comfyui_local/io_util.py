from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional, TextIO

import click
import typer


def read_workflow_json(workflow: Optional[Path]) -> dict[str, Any]:
    if workflow is not None:
        text = Path(workflow).expanduser().read_text(encoding="utf-8")
        return json.loads(text)
    text = sys.stdin.read()
    if not text.strip():
        raise typer.BadParameter("Provide --workflow PATH or pipe API-format workflow JSON on stdin")
    return json.loads(text)


def emit_json(data: Any, *, pretty: bool, file: Optional[TextIO] = None) -> None:
    if pretty:
        text = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        text = json.dumps(data, ensure_ascii=False)
    click.echo(text, file=file, nl=True)


def log_verbose(msg: str, *, verbose: bool, stream: TextIO = sys.stderr) -> None:
    if verbose:
        stream.write(msg + "\n")
        stream.flush()
