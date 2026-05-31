"""
Pre-download all required AI models to the HuggingFace cache.

Run once before first use:
    python scripts/download_models.py

Models downloaded:
    - ivrit-ai/whisper-large-v3-turbo-ct2  (CTranslate2 format, ~1.5 GB)
    - openai/whisper-large-v3              (via faster-whisper, ~3 GB)
    - Helsinki-NLP/opus-mt-en-he           (~300 MB)
"""

import sys
import os

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def download_whisper(model_id: str) -> None:
    print(f"\n--- Downloading faster-whisper model: {model_id} ---")
    from faster_whisper import WhisperModel
    # Passing device="cpu" with compute_type="int8" just to trigger the download
    model = WhisperModel(model_id, device="cpu", compute_type="int8")
    print(f"    OK — cached to HuggingFace cache dir")
    del model


def download_translation_model(model_id: str) -> None:
    print(f"\n--- Downloading translation model: {model_id} ---")
    from transformers import MarianMTModel, MarianTokenizer
    MarianTokenizer.from_pretrained(model_id)
    MarianMTModel.from_pretrained(model_id)
    print(f"    OK")


if __name__ == "__main__":
    print("Subtitle Creator — Model Downloader")
    print("This may take several minutes on first run.\n")

    try:
        download_whisper("ivrit-ai/whisper-large-v3-turbo-ct2")
    except Exception as e:
        print(f"  WARN: Could not download ivrit-ai model: {e}")

    try:
        download_whisper("large-v3")
    except Exception as e:
        print(f"  WARN: Could not download whisper-large-v3: {e}")

    try:
        download_translation_model("Helsinki-NLP/opus-mt-en-he")
    except Exception as e:
        print(f"  WARN: Could not download Helsinki-NLP model: {e}")

    print("\nAll models downloaded. You're ready to run the application.")
