"""
Python backend entry point.

Reads newline-delimited JSON commands from stdin.
Streams newline-delimited JSON events to stdout.
stderr is reserved for tracebacks / debug logging.

Expected stdin commands:
    {"type": "start_job", "job_id": "...", "video_path": "...", "pipeline": "heb_to_heb"|"any_to_heb"}
    {"type": "cancel_job", "job_id": "..."}
    {"type": "shutdown"}
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading

# Ensure backend/ is on PYTHONPATH regardless of working directory
sys.path.insert(0, os.path.dirname(__file__))

from ipc.protocol import (
    emit_complete,
    emit_error,
    emit_progress,
    emit_segment,
    stdin_reader,
)
from pipeline.audio_extractor import extract
from pipeline.srt_writer import Segment, srt_path_for, write_srt

_cancel_events: dict[str, threading.Event] = {}
_stop = threading.Event()


def _run_job(cmd: dict) -> None:
    job_id = cmd.get("job_id", "unknown")
    video_path = cmd.get("video_path", "")
    pipeline_name = cmd.get("pipeline", "heb_to_heb")

    cancel = threading.Event()
    _cancel_events[job_id] = cancel

    def _emit_progress(stage: str, percent: int, elapsed_s=None):
        if cancel.is_set():
            return
        emit_progress(job_id, stage, percent, elapsed_s)

    def _emit_error(message: str, recoverable: bool = False):
        emit_error(job_id, message, recoverable)

    wav_path = None
    try:
        # --- Stage: audio extraction ---
        _emit_progress("extracting_audio", 3)
        wav_path = extract(video_path)
        _emit_progress("extracting_audio", 7)

        if cancel.is_set():
            return

        # --- Stage: AI pipeline ---
        if pipeline_name == "heb_to_heb":
            from pipeline.heb_pipeline import run
        else:
            from pipeline.any_pipeline import run

        segments: list[Segment] = []
        for seg in run(wav_path, job_id, _emit_progress, _emit_error):
            if cancel.is_set():
                return
            emit_segment(job_id, seg.index, seg.start, seg.end, seg.text)
            segments.append(seg)

        if cancel.is_set():
            return

        # --- Stage: write SRT ---
        _emit_progress("writing_srt", 99)
        srt_path = srt_path_for(video_path)
        write_srt(segments, srt_path)

        emit_complete(job_id, srt_path, len(segments))

    except Exception as exc:
        sys.stderr.write(f"[job {job_id}] FATAL: {exc}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        emit_error(job_id, str(exc), recoverable=False)
    finally:
        _cancel_events.pop(job_id, None)
        if wav_path and os.path.isfile(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass


def _on_command(cmd: dict) -> None:
    t = cmd.get("type")

    if t == "start_job":
        thread = threading.Thread(target=_run_job, args=(cmd,), daemon=True)
        thread.start()

    elif t == "cancel_job":
        job_id = cmd.get("job_id")
        if job_id in _cancel_events:
            _cancel_events[job_id].set()

    elif t == "shutdown":
        _stop.set()


def main() -> None:
    reader_thread = threading.Thread(
        target=stdin_reader,
        args=(_on_command, _stop),
        daemon=True,
    )
    reader_thread.start()
    _stop.wait()


if __name__ == "__main__":
    main()
