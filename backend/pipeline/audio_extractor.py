"""Extract audio from any video container to a 16kHz mono PCM WAV via FFmpeg."""

import os
import shutil
import subprocess
import sys
import tempfile

_FFMPEG_FALLBACKS = [
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\FFmpeg\bin\ffmpeg.exe",
    r"C:\Program Files (x86)\FFmpeg\bin\ffmpeg.exe",
    r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
]

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _find_ffmpeg() -> str:
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    for candidate in _FFMPEG_FALLBACKS:
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(
        "ffmpeg not found. Download from https://ffmpeg.org/download.html and add to PATH."
    )


def extract(video_path: str, output_path: str | None = None) -> str:
    """Convert video to 16kHz mono WAV suitable for Whisper."""
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    ffmpeg_exe = _find_ffmpeg()

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-af", "aresample=async=1",
        output_path,
    ]

    result = subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,   # prevent FFmpeg from reading the C# IPC pipe
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_NO_WINDOW,
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed (exit {result.returncode})")

    return output_path
