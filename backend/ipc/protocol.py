"""
Newline-delimited JSON IPC protocol between Python backend and C# frontend.

Python writes to stdout; C# reads line-by-line.
C# writes to stdin; Python reads line-by-line.
"""

import json
import sys
import threading
from typing import Callable


def _emit(obj: dict) -> None:
    line = json.dumps(obj, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def emit_progress(job_id: str, stage: str, percent: int, elapsed_s: float | None = None) -> None:
    msg = {"type": "progress", "job_id": job_id, "stage": stage, "percent": percent}
    if elapsed_s is not None:
        msg["elapsed_s"] = round(elapsed_s, 1)
    _emit(msg)


def emit_segment(job_id: str, index: int, start: float, end: float, text: str) -> None:
    _emit({"type": "segment", "job_id": job_id, "index": index,
           "start": round(start, 3), "end": round(end, 3), "text": text})


def emit_complete(job_id: str, srt_path: str, segment_count: int) -> None:
    _emit({"type": "complete", "job_id": job_id,
           "srt_path": srt_path, "segment_count": segment_count})


def emit_error(job_id: str, message: str, recoverable: bool = False) -> None:
    _emit({"type": "error", "job_id": job_id,
           "message": message, "recoverable": recoverable})


def stdin_reader(on_command: Callable[[dict], None], stop_event: threading.Event) -> None:
    """Blocking loop that reads JSON commands from stdin and dispatches them."""
    # Force line-buffering on stdin — the default block-buffering on Windows
    # pipes means `for line in sys.stdin` waits for 8 KB before returning,
    # so the first command is never processed until a second one arrives.
    try:
        sys.stdin.reconfigure(line_buffering=True)
    except AttributeError:
        pass  # older Python fallback

    while not stop_event.is_set():
        raw_line = sys.stdin.readline()
        if not raw_line:          # EOF — C# closed stdin (app shutting down)
            break
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            cmd = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"[ipc] bad JSON on stdin: {exc}\n")
            sys.stderr.flush()
            continue
        on_command(cmd)
