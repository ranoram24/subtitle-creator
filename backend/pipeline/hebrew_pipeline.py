"""
Hebrew output pipeline: any-language audio → Hebrew SRT.

Step 1 — OpenAI Whisper (task="translate") → English segments with timestamps
Step 2 — GPT-4o-mini batch-translates the English lines to Hebrew

Timestamps from Step 1 are preserved exactly.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Generator
from typing import Callable

from pipeline.srt_writer import Segment

CHUNK_SECONDS = 600       # 10-min audio chunks for Whisper API
TRANSLATE_BATCH = 30      # subtitle lines per GPT call


def _log(msg: str) -> None:
    sys.stderr.write(f"[hebrew] {msg}\n")
    sys.stderr.flush()


_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _find_ffmpeg() -> str:
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    for c in [r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\FFmpeg\bin\ffmpeg.exe"]:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError("ffmpeg not found")


def _audio_duration(path: str) -> float:
    ffmpeg = _find_ffmpeg()
    ffprobe = ffmpeg.replace("ffmpeg.exe", "ffprobe.exe")
    if not os.path.isfile(ffprobe):
        return os.path.getsize(path) / 32000
    r = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, creationflags=_NO_WINDOW,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return os.path.getsize(path) / 32000


def _extract_chunk(audio_path: str, start_s: float, duration_s: float) -> str:
    ffmpeg = _find_ffmpeg()
    fd, out = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    subprocess.run(
        [ffmpeg, "-y", "-i", audio_path,
         "-ss", str(start_s), "-t", str(duration_s),
         "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", out],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW,
    )
    return out


def _translate_batch(client, english_lines: list[str]) -> list[str]:
    """Translate a batch of English subtitle lines to Hebrew using GPT-4o-mini."""
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(english_lines))

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional subtitle translator. "
                    "Translate each numbered English subtitle line to Hebrew. "
                    "Keep the same numbering. Translate naturally for movie/TV dialogue. "
                    "Return ONLY the numbered Hebrew lines, nothing else."
                ),
            },
            {"role": "user", "content": numbered},
        ],
        temperature=0.2,
    )

    result = response.choices[0].message.content.strip()
    hebrew_lines: list[str] = []
    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue
        if ". " in line:
            _, heb = line.split(". ", 1)
            hebrew_lines.append(heb.strip())
        else:
            hebrew_lines.append(line)

    # Safety: if GPT returned wrong count, pad/trim to match input length
    while len(hebrew_lines) < len(english_lines):
        hebrew_lines.append(english_lines[len(hebrew_lines)])
    return hebrew_lines[: len(english_lines)]


def run(
    audio_path: str,
    job_id: str,
    emit_progress: Callable[[str, int, float | None], None],
    emit_error: Callable[[str, bool], None],
) -> Generator[Segment, None, None]:

    from openai import OpenAI
    from pipeline.config import PROXY_BASE_URL
    client = OpenAI(api_key="proxy", base_url=f"{PROXY_BASE_URL}/v1")

    # ── Step 1: Whisper → English segments ──────────────────────────────────
    duration = _audio_duration(audio_path)
    n_chunks = max(1, math.ceil(duration / CHUNK_SECONDS))
    _log(f"Audio: {duration:.0f}s, {n_chunks} chunk(s). Transcribing to English first...")

    emit_progress("transcribing", 10, None)

    english_segs: list[tuple[float, float, str]] = []   # (start, end, text)

    for chunk_i in range(n_chunks):
        start_s = chunk_i * CHUNK_SECONDS
        chunk_duration = min(CHUNK_SECONDS, duration - start_s)

        if n_chunks > 1:
            chunk_path = _extract_chunk(audio_path, start_s, chunk_duration)
        else:
            chunk_path = audio_path
            start_s = 0.0

        _log(f"Whisper chunk {chunk_i + 1}/{n_chunks}...")
        try:
            with open(chunk_path, "rb") as f:
                resp = client.audio.translations.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                )
            for seg in resp.segments:
                english_segs.append((start_s + seg.start, start_s + seg.end, seg.text.strip()))
        finally:
            if n_chunks > 1 and os.path.isfile(chunk_path):
                os.remove(chunk_path)

        pct = min(10 + int(((chunk_i + 1) / n_chunks) * 40), 50)
        emit_progress("transcribing", pct, None)

    _log(f"Transcription done: {len(english_segs)} segments. Translating to Hebrew...")

    # ── Step 2: GPT-4o-mini → Hebrew ────────────────────────────────────────
    emit_progress("translating", 52, None)

    n_segs = len(english_segs)
    n_batches = max(1, math.ceil(n_segs / TRANSLATE_BATCH))
    hebrew_texts: list[str] = []

    for batch_i in range(n_batches):
        start = batch_i * TRANSLATE_BATCH
        batch = [t for _, _, t in english_segs[start: start + TRANSLATE_BATCH]]
        _log(f"Translating batch {batch_i + 1}/{n_batches} ({len(batch)} lines)...")
        hebrew_texts.extend(_translate_batch(client, batch))

        pct = min(52 + int(((batch_i + 1) / n_batches) * 46), 98)
        emit_progress("translating", pct, None)

    # ── Yield final Hebrew segments ──────────────────────────────────────────
    for index, ((start, end, _), heb) in enumerate(zip(english_segs, hebrew_texts), start=1):
        yield Segment(index=index, start=start, end=end, text=heb.strip())
