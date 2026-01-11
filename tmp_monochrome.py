from __future__ import annotations

import re
from pathlib import Path


def clamp(value: float, minimum: int = 0, maximum: int = 255) -> int:
    return max(minimum, min(maximum, int(round(value))))


def to_gray_hex(r: int, g: int, b: int) -> str:
    gray = clamp(0.299 * r + 0.587 * g + 0.114 * b)
    return f"{gray:02x}{gray:02x}{gray:02x}"


def hex_repl(match: re.Match[str]) -> str:
    hex_value = match.group(1)
    r = int(hex_value[0:2], 16)
    g = int(hex_value[2:4], 16)
    b = int(hex_value[4:6], 16)
    return f"#{to_gray_hex(r, g, b)}"


def rgb_repl(match: re.Match[str]) -> str:
    r = float(match.group(1))
    g = float(match.group(2))
    b = float(match.group(3))
    gray = clamp(0.299 * r + 0.587 * g + 0.114 * b)
    return f"rgb({gray}, {gray}, {gray})"


def rgba_repl(match: re.Match[str]) -> str:
    r = float(match.group(1))
    g = float(match.group(2))
    b = float(match.group(3))
    alpha = match.group(4)
    gray = clamp(0.299 * r + 0.587 * g + 0.114 * b)
    return f"rgba({gray}, {gray}, {gray}, {alpha})"


def hex0x_repl(match: re.Match[str]) -> str:
    hex_value = match.group(1)
    r = int(hex_value[0:2], 16)
    g = int(hex_value[2:4], 16)
    b = int(hex_value[4:6], 16)
    gray_hex = to_gray_hex(r, g, b)
    return f"0x{gray_hex.upper()}"


GLYPH_MAP = {
    "\u2013": "-",
    "\u2014": "-",
    "\u201c": '"',
    "\u201d": '"',
    "\u2022": "-",
    "\u2026": "...",
    "\u20e3": "",
    "\u2139": "i",
    "\u2192": "->",
    "\u2248": "~",
    "\u23f3": "[LOADING]",
    "\u23f8": "[PAUSE]",
    "\u25b6": ">",
    "\u25cf": "*",
    "\u26a0": "[ALERT]",
    "\u26a1": "[FAST]",
    "\u2705": "[OK]",
    "\u2713": "[OK]",
    "\u2717": "[NO]",
    "\u274c": "[FAIL]",
    "\u27f3": "[REFRESH]",
    "\ufe0f": "",
    "\U0001f3af": "[GOAL]",
    "\U0001f3c1": "[FINISH]",
    "\U0001f446": "^",
    "\U0001f4a1": "[IDEA]",
    "\U0001f4bc": "[WORK]",
    "\U0001f4c1": "[FILE]",
    "\U0001f4c8": "[CHART]",
    "\U0001f4ca": "[CHART]",
    "\U0001f4cb": "[NOTE]",
    "\U0001f4cd": "[PIN]",
    "\U0001f4da": "[DOCS]",
    "\U0001f4dd": "[NOTE]",
    "\U0001f4e6": "[PKG]",
    "\U0001f4f1": "[MOBILE]",
    "\U0001f4fa": "[LIVE]",
    "\U0001f504": "[LOOP]",
    "\U0001f50d": "[SEARCH]",
    "\U0001f50e": "[SEARCH]",
    "\U0001f517": "[LINK]",
    "\U0001f522": "[NUM]",
    "\U0001f52c": "[LAB]",
    "\U0001f534": "[BLOCKED]",
    "\U0001f5a5": "[DESKTOP]",
    "\U0001f5b1": "[MOUSE]",
    "\U0001f5c2": "[FOLDER]",
    "\U0001f680": "[LAUNCH]",
    "\U0001f6a8": "[ALERT]",
    "\U0001f7e2": "[PASS]",
}


def strip_glyphs(text: str) -> str:
    for source, replacement in GLYPH_MAP.items():
        text = text.replace(source, replacement)
    return text


def main() -> None:
    path = Path("templates/cockpit.html")
    text = path.read_text(encoding="utf-8")

    text = re.sub(r"#([0-9a-fA-F]{6})", hex_repl, text)
    text = re.sub(r"rgba\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)", rgba_repl, text)
    text = re.sub(r"rgb\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)", rgb_repl, text)
    text = re.sub(r"0x([0-9a-fA-F]{6})", hex0x_repl, text)

    text = strip_glyphs(text)
    path.write_text(text, encoding="utf-8")
    print("Converted templates/cockpit.html to grayscale palette.")


if __name__ == "__main__":
    main()
