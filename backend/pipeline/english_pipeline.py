"""
English output pipeline: any-language audio → English SRT.

Uses Whisper task="translate" which natively transcribes AND translates
to English in one pass, preserving accurate timestamps.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from typing import Callable

from pipeline.model_loader import load_whisper, get_batch_size
from pipeline.srt_writer import Segment

# "base" is ~150 MB and loads in seconds on CPU (~20x real-time).
# Switch to "large-v3" for production quality once a GPU is available.
MODEL = "base"

_VAD_PARAMS = {
    "min_silence_duration_ms": 500,
    "speech_pad_ms": 200,
}


def _log(msg: str) -> None:
    import sys
    sys.stderr.write(f"[pipeline] {msg}\n")
    sys.stderr.flush()


def run(
    audio_path: str,
    job_id: str,
    emit_progress: Callable[[str, int, float | None], None],
    emit_error: Callable[[str, bool], None],
) -> Generator[Segment, None, None]:
    _log("Importing faster-whisper...")
    from faster_whisper import BatchedInferencePipeline
    _log(f"faster-whisper imported. Loading model '{MODEL}'...")

    model = load_whisper(
        MODEL,
        emit_error=lambda msg, recoverable: emit_error(msg, recoverable),
    )
    _log(f"Model loaded. batch_size={get_batch_size()}. Starting transcription...")
    batch_size = get_batch_size()
    pipeline = BatchedInferencePipeline(model=model)

    emit_progress("transcribing", 10, None)
    t_start = time.monotonic()

    segments_iter, info = pipeline.transcribe(
        audio_path,
        task="translate",        # any language → English
        vad_filter=True,
        vad_parameters=_VAD_PARAMS,
        beam_size=2,
        batch_size=batch_size,
        word_timestamps=False,
    )

    total_duration = info.duration or 1.0

    for index, seg in enumerate(segments_iter, start=1):
        elapsed = time.monotonic() - t_start
        pct = min(10 + int((seg.end / total_duration) * 88), 98)
        emit_progress("transcribing", pct, elapsed)
        yield Segment(index=index, start=seg.start, end=seg.end, text=seg.text)
