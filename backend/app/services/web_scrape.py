"""Fetch and extract visible text from a public page (SSRF-hardened)."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "metadata.google.internal",
        "metadata.google",
    }
)
MAX_BYTES = 1_500_000
REQUEST_TIMEOUT = 22


def _host_ips(hostname: str) -> list[str]:
    out: list[str] = []
    for fam, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
        if fam == socket.AF_INET:
            out.append(sockaddr[0])
        elif fam == socket.AF_INET6:
            out.append(sockaddr[0])
    return out


def _ip_blocked(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
    )


def assert_safe_http_url(url: str) -> str:
    raw = (url or "").strip()
    if len(raw) > 2048:
        raise ValueError("URL is too long")
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are allowed")
    host = (parsed.hostname or "").lower()
    if not host or host in BLOCKED_HOSTS:
        raise ValueError("Host is not allowed")
    try:
        ipaddress.ip_address(host)
        if _ip_blocked(host):
            raise ValueError("IP targets are not allowed")
    except ValueError:
        pass
    try:
        for ip in _host_ips(host):
            if _ip_blocked(ip):
                raise ValueError("Host resolves to a blocked network")
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve host: {e}") from e
    return raw


def fetch_page_text(url: str) -> tuple[str, str]:
    """
    Returns (final_url_after_redirects, plain_text).
    """
    safe = assert_safe_http_url(url)
    headers = {
        "User-Agent": "InterviewCoachBot/1.0 (educational; contact admin)",
        "Accept": "text/html,text/plain,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }
    r = requests.get(
        safe,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )
    r.raise_for_status()
    final_url = str(r.url)
    assert_safe_http_url(final_url)
    chunk = r.content
    if len(chunk) > MAX_BYTES:
        raise ValueError("Page is too large to process")
    ctype = (r.headers.get("Content-Type") or "").lower()
    if "text/plain" in ctype or safe.lower().endswith(".txt"):
        text = chunk.decode("utf-8", errors="replace")
    else:
        soup = BeautifulSoup(chunk, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 80:
        raise ValueError(
            "Not enough text extracted (try a page with readable HTML or a .txt URL)"
        )
    return final_url, text[:120_000]
