"""Format subtitle segments into a valid SRT string or file."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Segment:
    index: int
    start: float   # seconds
    end: float     # seconds
    text: str


def _ts(seconds: float) -> str:
    """Convert float seconds to SRT timestamp: HH:MM:SS,mmm"""
    ms = int(round(seconds * 1000))
    h, remainder = divmod(ms, 3_600_000)
    m, remainder = divmod(remainder, 60_000)
    s, ms = divmod(remainder, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments_to_srt(segments: list[Segment]) -> str:
    blocks = []
    for seg in segments:
        blocks.append(f"{seg.index}\n{_ts(seg.start)} --> {_ts(seg.end)}\n{seg.text.strip()}\n")
    return "\n".join(blocks)


def write_srt(segments: list[Segment], output_path: str) -> None:
    """Write segments to a UTF-8 SRT file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8-sig") as f:
        f.write(segments_to_srt(segments))


def srt_path_for(video_path: str) -> str:
    """Return the default .srt path alongside the source video."""
    base, _ = os.path.splitext(video_path)
    return base + ".srt"
