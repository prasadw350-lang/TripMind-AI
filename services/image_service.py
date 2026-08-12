"""Destination imagery via Unsplash, with a deterministic safe fallback."""
import hashlib
import threading
import urllib.parse

import requests

from config import config

_cache = {}
_lock = threading.Lock()

FALLBACKS = [
    "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=1200&q=70",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=70",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=70",
    "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1200&q=70",
    "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?auto=format&fit=crop&w=1200&q=70",
    "https://images.unsplash.com/photo-1504609773096-104ff2c73ba4?auto=format&fit=crop&w=1200&q=70",
]


def _fallback(query: str) -> str:
    digest = hashlib.md5(query.encode("utf-8")).hexdigest()
    return FALLBACKS[int(digest, 16) % len(FALLBACKS)]


def get_image(query: str, orientation: str = "landscape") -> str:
    """Return an image URL for `query`. Never raises."""
    query = (query or "travel").strip()
    key = f"{query}|{orientation}"
    with _lock:
        if key in _cache:
            return _cache[key]

    url = None
    if config.UNSPLASH_ACCESS_KEY:
        try:
            resp = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "per_page": 1, "orientation": orientation},
                headers={"Authorization": f"Client-ID {config.UNSPLASH_ACCESS_KEY}"},
                timeout=8,
            )
            if resp.ok:
                items = resp.json().get("results") or []
                if items:
                    url = items[0]["urls"].get("regular") or items[0]["urls"].get("small")
        except requests.RequestException:
            url = None

    if not url:
        # Keyword-seeded source that still varies per destination.
        url = (
            "https://source.unsplash.com/1200x800/?"
            + urllib.parse.quote(f"{query},travel")
        )
        try:
            head = requests.head(url, timeout=5, allow_redirects=True)
            if not head.ok:
                url = _fallback(query)
        except requests.RequestException:
            url = _fallback(query)

    with _lock:
        _cache[key] = url
    return url


def get_images(queries):
    return {q: get_image(q) for q in queries}
