"""Text helpers shared by the ingest and scoring paths: HTML to text and the climate-passage
filter that keeps LLM input small and focused. Pure functions, no network, market-neutral."""

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
