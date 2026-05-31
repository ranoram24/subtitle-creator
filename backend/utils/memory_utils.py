"""GPU/CPU memory probing to select optimal compute settings at runtime."""

import sys


def get_free_vram_gb() -> float:
    """Returns free VRAM in GB, or 0.0 if CUDA is unavailable."""
    try:
        import torch
        if not torch.cuda.is_available():
            return 0.0
        free, _ = torch.cuda.mem_get_info()
        return free / (1024 ** 3)
    except Exception:
        return 0.0


def select_compute_type(free_vram_gb: float) -> tuple[str, str]:
    """Returns (device, compute_type) based on available VRAM."""
    if free_vram_gb >= 6.0:
        return "cuda", "int8_float16"
    elif free_vram_gb >= 3.0:
        return "cuda", "int8"
    else:
        return "cpu", "int8"


def select_batch_size(free_vram_gb: float) -> int:
    """Returns a safe batch_size for BatchedInferencePipeline."""
    if free_vram_gb >= 8.0:
        return 8
    elif free_vram_gb >= 4.0:
        return 4
    else:
        return 1
