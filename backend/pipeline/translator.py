"""
Helsinki-NLP/opus-mt-en-he batch translator.

Translates English text strings to Hebrew while keeping the caller's
timestamps — each input string maps 1-to-1 to an output string.
"""

from __future__ import annotations

TRANSLATION_MODEL = "Helsinki-NLP/opus-mt-en-he"
_BATCH_SIZE = 32

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline
        _pipeline = pipeline(
            "translation",
            model=TRANSLATION_MODEL,
            tokenizer=TRANSLATION_MODEL,
            device=-1,          # CPU — translation model is small; GPU not worth the VRAM
            batch_size=_BATCH_SIZE,
        )
    return _pipeline


def translate_batch(texts: list[str]) -> list[str]:
    """
    Translate a list of English strings to Hebrew.

    Returns a list of the same length; order is preserved.
    Empty or whitespace-only strings are passed through unchanged.
    """
    if not texts:
        return []

    pipe = _get_pipeline()
    indices_to_translate = [i for i, t in enumerate(texts) if t.strip()]
    inputs = [texts[i] for i in indices_to_translate]

    results = pipe(inputs, max_length=512)
    translated = [r["translation_text"] for r in results]

    output = list(texts)
    for orig_i, heb in zip(indices_to_translate, translated):
        output[orig_i] = heb

    return output
