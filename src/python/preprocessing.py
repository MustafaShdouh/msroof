"""Versioned preprocessing shared by Masroof training and Python verification."""

from __future__ import annotations

import re


PREPROCESSING_CONTRACT_VERSION = "1.1.0"
_FINANCIAL_NUMBERS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫٬", "01234567890123456789.,")
_ROUTING_PREFIX = re.compile(r"^[A-Z]{2}(\r?\n|\s+)")
_ARABIC_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670]")
_WHITESPACE = re.compile(r"\s+")
_LONG_NUMBER = re.compile(r"(?<![A-Za-z0-9_])[0-9]{6,}(?![A-Za-z0-9_])")
_TOKEN = re.compile(r"[A-Za-z0-9_\u0621-\u064A\u0660-\u0669*\.\-]+")


def normalize_financial_numbers(text: str) -> str:
    """Canonicalize Arabic/Persian digits and Arabic decimal/group separators.

    Preserve Arabic letters, currency wording, and the Arabic comma U+060C.
    This is safe for model input and raw entity extraction, unlike lowercasing
    or replacing long numbers, which must only happen in model preprocessing.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return text.translate(_FINANCIAL_NUMBERS)


def preprocess_message(text: str) -> str:
    normalized = normalize_financial_numbers(text).replace("\\n", "\n").replace("\r", "")
    normalized = _ROUTING_PREFIX.sub("", normalized)
    normalized = _ARABIC_DIACRITICS.sub("", normalized)
    normalized = _WHITESPACE.sub(" ", normalized)
    normalized = _LONG_NUMBER.sub(" NUM_LONG ", normalized)
    return normalized.strip().lower()


def tokenize_features(normalized_text: str) -> list[str]:
    tokens = _TOKEN.findall(normalized_text)
    return tokens + [f"{tokens[index]} {tokens[index + 1]}" for index in range(len(tokens) - 1)]
