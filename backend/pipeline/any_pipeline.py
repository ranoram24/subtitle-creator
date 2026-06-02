"""
Any-to-Heb pipeline (pivot strategy):
  Step 1 — faster-whisper with task="translate" → timestamped English segments
  Step 2 — Helsinki-NLP/opus-mt-en-he batch translation → Hebrew text

Timestamps from Step 1 are preserved unchanged into the final SRT.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from typing import Callable

from pipeline.model_loader import load_whisper, get_batch_size
from pipeline.srt_writer import Segment
from pipeline.translator import translate_batch

# Prefer large-v3 for best multilingual quality; fall back to the turbo model
# if large-v3 is not yet cached (avoids a 3 GB download on first run).
import os as _os, pathlib as _pathlib
def _pick_whisper_model() -> str:
    hf_cache = _pathlib.Path(_os.environ.get("HF_HOME", _os.path.expanduser("~/.cache/huggingface/hub")))
    large_v3_cached = any(hf_cache.glob("models--Systran--faster-whisper-large-v3/snapshots/*/model.bin"))
    return "large-v3" if large_v3_cached else "ivrit-ai/whisper-large-v3-turbo-ct2"

TRANSLATE_MODEL = _pick_whisper_model()

_VAD_PARAMS = {
    "min_silence_duration_ms": 500,
    "speech_pad_ms": 200,
}

_TRANSLATION_BATCH = 32        # segments per Helsinki-NLP batch call


def run(
    audio_path: str,
    job_id: str,
    emit_progress: Callable[[str, int, float | None], None],
    emit_error: Callable[[str, bool], None],
) -> Generator[Segment, None, None]:
    """
    Transcribe foreign-language audio and yield Hebrew Segment objects.

    Stages reported via emit_progress: loading_model → transcribing → translating.
    """
    from faster_whisper import BatchedInferencePipeline
    model = load_whisper(
        TRANSLATE_MODEL,
        emit_error=lambda msg, recoverable: emit_error(msg, recoverable),
    )
    batch_size = get_batch_size()
    pipeline = BatchedInferencePipeline(model=model)

    emit_progress("transcribing", 10, None)
    t_start = time.monotonic()

    segments_iter, info = pipeline.transcribe(
        audio_path,
        task="translate",        # Whisper natively outputs English
        vad_filter=True,
        vad_parameters=_VAD_PARAMS,
        beam_size=2,
        batch_size=batch_size,
        word_timestamps=False,
    )

    total_duration = info.duration or 1.0
    english_segments: list[tuple[float, float, str]] = []

    for seg in segments_iter:
        elapsed = time.monotonic() - t_start
        pct = min(10 + int((seg.end / total_duration) * 44), 54)
        emit_progress("transcribing", pct, elapsed)
        english_segments.append((seg.start, seg.end, seg.text))

    # --- Step 2: batch-translate English → Hebrew ---
    emit_progress("translating", 55, None)
    english_texts = [t for _, _, t in english_segments]
    total = len(english_texts)
    hebrew_texts: list[str] = []

    for batch_start in range(0, total, _TRANSLATION_BATCH):
        batch = english_texts[batch_start: batch_start + _TRANSLATION_BATCH]
        hebrew_texts.extend(translate_batch(batch))
        pct = min(55 + int(((batch_start + len(batch)) / max(total, 1)) * 43), 98)
        emit_progress("translating", pct, time.monotonic() - t_start)

    for index, ((start, end, _), heb) in enumerate(zip(english_segments, hebrew_texts), start=1):
        yield Segment(index=index, start=start, end=end, text=heb)
