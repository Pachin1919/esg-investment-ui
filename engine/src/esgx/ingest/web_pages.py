"""Company website helpers for the about-page finder: site URL, on-site links, a keyword fallback.

The about page is the firm's self-description, so everything derived from it is TALK
(Giannetti et al. 2023). Pure functions except `company_website` (yfinance) and `fetch_html`.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

_HEADERS = {"User-Agent": "Mozilla/5.0 (esgx research)"}
ABOUT_HINTS = ("about us", "about", "who we are", "our company", "company profile", "corporate profile",
               "overview", "關於", "关于", "公司簡介", "公司简介", "集團簡介", "集团简介")
_SKIP = ("javascript:", "mailto:", "tel:", "#")


def company_website(firm_id: str) -> str | None:
    """Homepage URL from yfinance `.info['website']` (None if unknown)."""
    import yfinance as yf

    try:
        return yf.Ticker(firm_id).info.get("website") or None
    except Exception:  # noqa: BLE001 - yfinance raises many types; a missing site is not fatal
        return None


def fetch_html(url: str, timeout: int = 30) -> str:
    r = requests.get(url, headers=_HEADERS, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    return r.text


def page_links(html: str, base_url: str, max_links: int = 150) -> list[dict]:
    """Same-site links as [{'text', 'url'}], first occurrence of each URL, in page order."""
    host = urlparse(base_url).netloc.removeprefix("www.")
    seen: set[str] = set()
    out: list[dict] = []
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(_SKIP):
            continue
        url = urljoin(base_url, href).split("#")[0]
        if urlparse(url).netloc.removeprefix("www.") != host or url in seen:
            continue
        seen.add(url)
        out.append({"text": " ".join(a.get_text(" ").split())[:80], "url": url})
        if len(out) >= max_links:
            break
    return out


def heuristic_about(links: list[dict]) -> dict | None:
    """Keyword fallback (dry run / no key): the link whose text or path best matches ABOUT_HINTS."""
    best, best_rank = None, len(ABOUT_HINTS)
    for link in links:
        hay = f"{link['text']} {urlparse(link['url']).path.replace('-', ' ').replace('_', ' ')}".lower()
        for rank, hint in enumerate(ABOUT_HINTS):
            if hint in hay and rank < best_rank:
                best, best_rank = link, rank
                break
    return best


def page_text(html: str, max_chars: int = 20_000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return "\n".join(line for line in (s.strip() for s in soup.get_text("\n").splitlines()) if line)[:max_chars]
