from __future__ import annotations

import sys
from typing import TextIO


def to_safe_ascii(text: str) -> str:
    """Convert text to ASCII-safe representation for narrow console encodings."""
    return text.encode("ascii", errors="backslashreplace").decode("ascii")


def safe_print(message: object = "", *, file: TextIO | None = None, end: str = "\n") -> None:
    """Print with Unicode fallback for Windows cp1252-like consoles."""
    target = file or sys.stdout
    text = str(message)
    try:
        print(text, file=target, end=end)
    except UnicodeEncodeError:
        print(to_safe_ascii(text), file=target, end=end)
