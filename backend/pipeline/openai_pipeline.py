"""
OpenAI Whisper API pipeline: any-language audio → English SRT.

Handles long audio by splitting into 10-minute chunks (API limit is 25 MB;
16kHz mono WAV ≈ 1.9 MB/min, so 10 min ≈ 19 MB — safely under the cap).
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

CHUNK_MINUTES = 10
CHUNK_SECONDS = CHUNK_MINUTES * 60

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _log(msg: str) -> None:
    sys.stderr.write(f"[openai] {msg}\n")
    sys.stderr.flush()


def _find_ffmpeg() -> str:
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    for c in [r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\FFmpeg\bin\ffmpeg.exe"]:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError("ffmpeg not found")


def _audio_duration(audio_path: str) -> float:
    """Return duration in seconds via ffprobe."""
    ffmpeg = _find_ffmpeg()
    ffprobe = ffmpeg.replace("ffmpeg.exe", "ffprobe.exe")
    if not os.path.isfile(ffprobe):
        # Fallback: estimate from file size (16kHz mono 16-bit = 32000 B/s)
        return os.path.getsize(audio_path) / 32000
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, creationflags=_NO_WINDOW,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return os.path.getsize(audio_path) / 32000


def _extract_chunk(audio_path: str, start_s: float, duration_s: float) -> str:
    """Extract a time slice from a WAV file into a temp file."""
    ffmpeg = _find_ffmpeg()
    fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    subprocess.run(
        [ffmpeg, "-y", "-i", audio_path,
         "-ss", str(start_s), "-t", str(duration_s),
         "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
         out_path],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=_NO_WINDOW,
    )
    return out_path


def run(
    audio_path: str,
    job_id: str,
    emit_progress: Callable[[str, int, float | None], None],
    emit_error: Callable[[str, bool], None],
) -> Generator[Segment, None, None]:

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OpenAI API key not set. Open the Settings tab and enter your key."
        )

    _log("Connecting to OpenAI API...")
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    duration = _audio_duration(audio_path)
    n_chunks = max(1, math.ceil(duration / CHUNK_SECONDS))
    _log(f"Audio duration: {duration:.0f}s → {n_chunks} chunk(s) of {CHUNK_MINUTES} min")

    emit_progress("transcribing", 10, None)

    index = 1
    for chunk_i in range(n_chunks):
        start_s = chunk_i * CHUNK_SECONDS
        chunk_duration = min(CHUNK_SECONDS, duration - start_s)

        if n_chunks > 1:
            _log(f"Chunk {chunk_i + 1}/{n_chunks} ({start_s:.0f}s – {start_s + chunk_duration:.0f}s)")
            chunk_path = _extract_chunk(audio_path, start_s, chunk_duration)
        else:
            chunk_path = audio_path   # single chunk — use original
            start_s = 0.0

        try:
            _log(f"Sending chunk {chunk_i + 1}/{n_chunks} to Whisper API...")
            with open(chunk_path, "rb") as f:
                response = client.audio.translations.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                )
            _log(f"Chunk {chunk_i + 1} done — {len(response.segments)} segments")

            for seg in response.segments:
                yield Segment(
                    index=index,
                    start=start_s + seg.start,
                    end=start_s + seg.end,
                    text=seg.text.strip(),
                )
                index += 1

        except Exception as exc:
            _log(f"API error on chunk {chunk_i + 1}: {exc}")
            raise
        finally:
            if n_chunks > 1 and os.path.isfile(chunk_path):
                os.remove(chunk_path)

        pct = min(10 + int(((chunk_i + 1) / n_chunks) * 88), 98)
        emit_progress("transcribing", pct, None)
