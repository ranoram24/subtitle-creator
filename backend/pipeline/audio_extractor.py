"""Extract audio from any video container to a 16kHz mono PCM WAV via FFmpeg."""

import os
import shutil
import subprocess
import tempfile

# Common Windows install paths tried when ffmpeg is not on PATH
_FFMPEG_FALLBACKS = [
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\FFmpeg\bin\ffmpeg.exe",
    r"C:\Program Files (x86)\FFmpeg\bin\ffmpeg.exe",
    r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
]


def _find_ffmpeg() -> str:
    """Return the ffmpeg executable path, searching PATH then common locations."""
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path
    for candidate in _FFMPEG_FALLBACKS:
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(
        "ffmpeg not found on PATH or common install locations. "
        "Download from https://ffmpeg.org/download.html and add to PATH."
    )


def extract(video_path: str, output_path: str | None = None) -> str:
    """
    Convert video to 16kHz mono WAV suitable for Whisper.

    Args:
        video_path:   Absolute path to the source video file.
        output_path:  Optional explicit output path. If None, a temp file is created
                      in the system temp dir; the caller is responsible for deletion.

    Returns:
        Absolute path to the output WAV file.

    Raises:
        FileNotFoundError: If video_path does not exist or FFmpeg cannot be located.
        RuntimeError:      If FFmpeg exits with a non-zero return code.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    ffmpeg_exe = _find_ffmpeg()

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

    cmd = [
        ffmpeg_exe,
        "-y",                     # overwrite without prompting
        "-i", video_path,
        "-vn",                    # strip video stream
        "-acodec", "pcm_s16le",   # 16-bit PCM
        "-ar", "16000",           # 16kHz sample rate required by Whisper
        "-ac", "1",               # mono
        output_path,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )

    return output_path
