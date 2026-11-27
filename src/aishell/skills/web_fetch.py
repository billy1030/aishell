"""Built-in clean web page reader (<fetch_url>) for aishell."""

import html
import re
import urllib.request
from typing import Optional

_FETCH_URL_RE = re.compile(r"<fetch_url>\s*(https?://[^\s<]+)\s*</fetch_url>", re.IGNORECASE)
_STRIP_TAGS_RE = re.compile(
    r"<(script|style|nav|header|footer|aside|noscript|svg)[^>]*>[\s\S]*?</\1>",
    re.IGNORECASE,
)
_MAIN_BLOCK_RE = re.compile(r"<(?:main|article)[^>]*>([\s\S]*?)</(?:main|article)>", re.IGNORECASE)


def extract_fetch_url_from_text(text: str) -> Optional[str]:
    """Extract the first <fetch_url>https://...</fetch_url> target from LLM output."""
    if not text:
        return None
    m = _FETCH_URL_RE.search(text)
    return m.group(1).strip() if m else None


def clean_html_to_text(raw_html: str, max_chars: int = 6000) -> str:
    """Strip navigation/script boilerplate from HTML and return clean readable text."""
    body = raw_html
    main_match = _MAIN_BLOCK_RE.search(body)
    if main_match and len(main_match.group(1)) > 200:
        body = main_match.group(1)

    body = _STRIP_TAGS_RE.sub("", body)
    body = re.sub(r"<[^>]+>", "\n", body)
    body = html.unescape(body)
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    cleaned = "\n".join(lines)
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n...[truncated]..."
    return cleaned


def fetch_url_clean(url: str, max_chars: int = 6000, timeout: float = 15.0) -> str:
    """Fetch a URL over HTTP/HTTPS and return cleaned readable text."""
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("Only http:// and https:// URLs are supported.")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; aishell/0.1.3)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return clean_html_to_text(raw, max_chars=max_chars)
