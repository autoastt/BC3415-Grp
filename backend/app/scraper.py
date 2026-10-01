"""Fetch a URL safely (SSRF guard, size cap) and reduce HTML to readable text."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Comment

from .config import config
from .ingestion import IngestionError, clean_text

_STRIP_TAGS = ["script", "style", "noscript", "nav", "footer", "header", "aside",
               "form", "iframe", "svg", "template", "button", "select", "object", "embed"]


def check_url(url: str) -> None:
    """Block non-http(s) schemes and any host that resolves to a non-public address
    (localhost, 10.x, 169.254.169.254 cloud metadata, etc.)."""
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or not p.hostname:
        raise IngestionError("Enter a full http:// or https:// address.")
    if p.username or p.password:
        raise IngestionError("URLs with embedded credentials aren't allowed.")
    if config.allow_private_urls:
        return
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror as e:
        raise IngestionError(f"Couldn't find the site '{p.hostname}'.") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise IngestionError("That address points to a private or internal network and can't be scraped.")


def fetch(url: str, max_redirects: int = 3) -> tuple[str, str]:
    """Returns (final_url, body). Redirects are followed manually so each hop is re-checked."""
    limit = config.max_scrape_mb * 1024 * 1024
    headers = {"User-Agent": f"{config.app_name}-KB-Ingest/1.0"}
    with httpx.Client(timeout=15, follow_redirects=False, headers=headers) as client:
        for _ in range(max_redirects + 1):
            check_url(url)
            with client.stream("GET", url) as r:
                if r.is_redirect:
                    loc = r.headers.get("location")
                    if not loc:
                        raise IngestionError("The site sent a redirect with no destination.")
                    url = urljoin(url, loc)
                    continue
                if r.status_code >= 400:
                    raise IngestionError(f"The site responded with HTTP {r.status_code}.")
                ctype = r.headers.get("content-type", "").lower()
                if not any(t in ctype for t in ("text/html", "text/plain", "application/xhtml")):
                    raise IngestionError(f"Only web pages can be scraped (got '{ctype or 'unknown'}').")
                body = bytearray()
                for chunk in r.iter_bytes():
                    body.extend(chunk)
                    if len(body) > limit:
                        raise IngestionError(f"The page is larger than {config.max_scrape_mb} MB.")
                encoding = r.encoding or "utf-8"
                return url, body.decode(encoding, errors="replace")
    raise IngestionError("Too many redirects.")


def html_to_text(html: str) -> tuple[str, str]:
    """Returns (page_title, readable_text)."""
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for tag in soup(_STRIP_TAGS):
        tag.decompose()
    for tag in soup.select('[role="navigation"],[role="banner"],[role="contentinfo"],[aria-hidden="true"],[hidden]'):
        tag.decompose()
    # Hidden-by-CSS text is a classic indirect prompt-injection vector
    for tag in soup.select('[style*="display:none"],[style*="display: none"],[style*="visibility:hidden"]'):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    return title, clean_text(root.get_text("\n"))


def scrape(url: str) -> tuple[str, str, str]:
    """Returns (final_url, title, text)."""
    final_url, body = fetch(url.strip())
    title, text = html_to_text(body) if "<" in body[:2000] else ("", clean_text(body))
    if len(text) < 50:
        raise IngestionError("Couldn't find readable text on that page. It may need JavaScript to render.")
    return final_url, title or urlparse(final_url).hostname or final_url, text
