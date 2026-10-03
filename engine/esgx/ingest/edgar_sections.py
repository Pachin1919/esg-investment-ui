"""Parsing of SEC filings: HTML to text, 10-K / 10-Q item splitting, climate-passage filter.
Pure functions, no network. Used by `edgar_text.load_documents` and by the preprocess agent."""

from __future__ import annotations

import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "head"]):
        t.decompose()
    # make block-level elements paragraph boundaries (inline-XBRL filers wrap everything in <div>/<span>)
    for tag in soup.find_all(["p", "div", "tr", "li", "br", "h1", "h2", "h3", "h4", "table"]):
        tag.insert_after("\n\n")
    text = soup.get_text(" ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


# --- 10-K / 10-Q section splitting -------------------------------------------------------
_ITEM_RE = re.compile(r"^\s*item\s+(\d{1,2}[a-c]?)\s*[\.:\-–—]?\s*(.{0,80})$", re.IGNORECASE | re.MULTILINE)

SECTIONS_10K = {"1": "business", "1a": "risk_factors", "7": "mdna"}
SECTIONS_10Q = {"2": "mdna", "1a": "risk_factors"}
MIN_SECTION_CHARS = 2000


def split_items(text: str, wanted: dict[str, str]) -> dict[str, str]:
    """Return {section_name: text} for wanted items. Picks the *longest* occurrence of each
    item (the table of contents produces short duplicates)."""
    matches = list(_ITEM_RE.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = m.group(1).lower()
        if key not in wanted:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[m.start():end].strip()
        name = wanted[key]
        if len(chunk) > len(out.get(name, "")):
            out[name] = chunk
    return out


# --- climate-relevance filter (keeps LLM input small and focused) ------------------------
CLIMATE_TERMS = [
    "climate", "carbon", "emission", "greenhouse", "ghg", "net zero", "net-zero", "renewable",
    "sustainab", "decarbon", "scope 1", "scope 2", "scope 3", "paris agreement", "energy transition",
    "environmental", "esg", "clean energy", "solar", "wind power", "electric vehicle", "methane",
    "carbon tax", "cap-and-trade", "emissions trading", "cbam", "csrd", "tcfd", "science based target",
    "biodiversity", "water usage", "waste", "pollution", "fossil", "coal", "natural gas",
]
_TERM_RE = re.compile("|".join(re.escape(t) for t in CLIMATE_TERMS), re.IGNORECASE)


def climate_passages(text: str, window: int = 1, max_chars: int = 60_000) -> tuple[str, float]:
    """Paragraphs mentioning climate terms (+/- `window` neighbours), joined; and the share
    of paragraphs that mention them (a cheap 'talk intensity' measure)."""
    paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 40]
    if not paras:
        return "", 0.0
    hit = [bool(_TERM_RE.search(p)) for p in paras]
    keep = set()
    for i, h in enumerate(hit):
        if h:
            keep.update(range(max(0, i - window), min(len(paras), i + window + 1)))
    out = "\n\n".join(paras[i] for i in sorted(keep))
    return out[:max_chars], sum(hit) / len(paras)
