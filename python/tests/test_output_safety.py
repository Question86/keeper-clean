import io

from output_safety import safe_print


class FragileAsciiStream(io.StringIO):
    """Simulates cp1252-like console that rejects non-ASCII writes."""

    def write(self, s: str) -> int:  # type: ignore[override]
        if any(ord(ch) > 127 for ch in s):
            raise UnicodeEncodeError("charmap", s, 0, 1, "character maps to <undefined>")
        return super().write(s)


def test_safe_print_falls_back_on_encoding_error():
    stream = FragileAsciiStream()
    safe_print("status ✅", file=stream)
    out = stream.getvalue()
    assert "\\u2705" in out


def test_safe_print_preserves_unicode_on_utf8_stream():
    stream = io.StringIO()
    safe_print("status ✅", file=stream)
    out = stream.getvalue()
    assert "✅" in out
