"""
Quantized Whisper model loader with automatic OOM fallback cascade.

Priority: CUDA int8_float16 → CUDA int8 → CPU int8
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from utils.memory_utils import get_free_vram_gb, select_batch_size

if TYPE_CHECKING:
    from faster_whisper import WhisperModel


_COMPUTE_CASCADE = [
    ("cuda", "int8_float16"),
    ("cuda", "int8"),
    ("cpu",  "int8"),
]


def load_whisper(model_name: str, emit_error=None) -> "WhisperModel":
    """
    Load a faster-whisper model with the best available device/precision.

    Args:
        model_name:  HuggingFace model ID or local path.
        emit_error:  Optional callable(message, recoverable) for IPC error events.

    Returns:
        Loaded WhisperModel instance.
    """
    from faster_whisper import WhisperModel

    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except ImportError:
        cuda_available = False

    for device, compute_type in _COMPUTE_CASCADE:
        if device == "cuda" and not cuda_available:
            continue
        try:
            model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                cpu_threads=4,
                num_workers=2,
            )
            sys.stderr.write(f"[model_loader] Loaded {model_name} on {device}/{compute_type}\n")
            return model
        except RuntimeError as exc:
            msg = f"[model_loader] {device}/{compute_type} failed: {exc} — trying next option"
            sys.stderr.write(msg + "\n")
            if emit_error:
                emit_error(msg, recoverable=True)

    raise RuntimeError(
        f"Could not load model '{model_name}' on any device/precision combination."
    )


def get_batch_size() -> int:
    return select_batch_size(get_free_vram_gb())
