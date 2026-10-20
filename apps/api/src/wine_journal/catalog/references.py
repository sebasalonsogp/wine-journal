"""Validation shared by catalog import and public outbound references."""

from urllib.parse import urlsplit

from pydantic import HttpUrl


def safe_reference(value: str) -> str:
    # Reject malformed hosts as well as schemes; the web uses these URLs as links.
    HttpUrl(value)
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or "." not in parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
        or "\\" in value
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("Use a plain HTTPS source URL without credentials or query strings.")
    return value
