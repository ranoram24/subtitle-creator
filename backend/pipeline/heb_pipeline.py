"""
Heb-to-Heb pipeline: Hebrew audio → Hebrew subtitles.

Uses ivrit-ai/whisper-large-v3-turbo-ct2 via faster-whisper with VAD filtering
and BatchedInferencePipeline for GPU-parallel segment encoding.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from typing import Callable

from pipeline.model_loader import load_whisper, get_batch_size
from pipeline.srt_writer import Segment

HEB_MODEL = "ivrit-ai/whisper-large-v3-turbo-ct2"

_VAD_PARAMS = {
    "min_silence_duration_ms": 500,
    "speech_pad_ms": 200,
}


def run(
    audio_path: str,
    job_id: str,
    emit_progress: Callable[[str, int, float | None], None],
    emit_error: Callable[[str, bool], None],
) -> Generator[Segment, None, None]:
    """
    Transcribe Hebrew audio and yield Segment objects as they are decoded.

    Args:
        audio_path:     Path to the 16kHz mono WAV file.
        job_id:         IPC job identifier (forwarded to emitters).
        emit_progress:  Callable(stage, percent, elapsed_s).
        emit_error:     Callable(message, recoverable).

    Yields:
        Segment instances in chronological order.
    """
    from faster_whisper import BatchedInferencePipeline
    model = load_whisper(
        HEB_MODEL,
        emit_error=lambda msg, recoverable: emit_error(msg, recoverable),
    )
    batch_size = get_batch_size()

    pipeline = BatchedInferencePipeline(model=model)

    emit_progress("transcribing", 10, None)
    t_start = time.monotonic()

    segments_iter, info = pipeline.transcribe(
        audio_path,
        language="he",
        task="transcribe",
        vad_filter=True,
        vad_parameters=_VAD_PARAMS,
        beam_size=2,
        batch_size=batch_size,
        word_timestamps=False,
    )

    total_duration = info.duration or 1.0
    index = 0

    for seg in segments_iter:
        index += 1
        elapsed = time.monotonic() - t_start
        percent = min(10 + int((seg.end / total_duration) * 88), 98)
        emit_progress("transcribing", percent, elapsed)
        yield Segment(index=index, start=seg.start, end=seg.end, text=seg.text)
