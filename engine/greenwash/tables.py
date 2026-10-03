"""Conservative parser for one-series, explicitly headed year tables."""
import re
import unicodedata

YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
UNIT = (r"(?:thousand\s+(?:metric\s+)?tonnes?\s+(?:of\s+)?CO2-?e"
        r"|million\s+(?:metric\s+)?(?:tonnes?|t)\s+(?:of\s+)?CO2-?e"
        r"|(?:metric\s+)?tonnes?\s+(?:of\s+)?CO2-?e"
        r"|ktCO2-?e|MtCO2-?e|tCO2-?e)")
ROW = re.compile(r"^(?P<label>\S.*?)\s+(?P<unit>"+UNIT+r")\s+(?P<cells>.+)$", re.I)
# Some reports put the unit inside the row label, e.g.
# "Direct (Scope 1) GHG emissions (million T of CO2e) [4]    6.05   6.64".
ROW_LABELLED_UNIT = re.compile(r"^(?P<label>\S.*?)\s*\((?P<unit>"+UNIT+r")\)\s*(?:\[\d+\])?\s+(?P<cells>.+)$", re.I)
CELL = re.compile(r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:\[\d+\])?|n/a|[-–]", re.I)


def unit_multiplier(unit_text):
    """Canonicalise a disclosed unit to tonnes of CO2e without guessing."""
    compact = re.sub(r"[\s\-]", "", unit_text.lower())
    if compact.startswith("million") or compact.startswith("mt"):
        return 1e6
    if compact.startswith("thousand") or compact.startswith("kt"):
        return 1e3
    return 1.0


def parse_tables(text):
    lines = text.splitlines()
    header = None
    group = None
    rows, warnings = [], []
    for number, line in enumerate(lines, 1):
        normalized = unicodedata.normalize('NFKC',line)
        years = [int(x) for x in YEAR.findall(normalized)]
        # Explicit column header, not an arbitrary sentence mentioning years.
        header_residue = YEAR.sub('',normalized)
        residue = re.sub(r'\b(?:KPI|Unit|Indicator|Metric|Year|FY|Fiscal|Reporting|Period)s?\b','',header_residue,flags=re.I)
        residue_words = re.findall(r"[A-Za-z\u4e00-\u9fff]+", residue)
        ordered = years == sorted(years) or years == sorted(years, reverse=True)
        # A short leading caption ("Environmental 2024 2023 2022") is still a column header;
        # a sentence that merely mentions years is not.
        is_header = len(years)>=2 and (not residue_words or (len(years)>=3 and len(residue_words)<=2 and ordered))
        if is_header:
            header = (number, line, years)
            group = None
            continue
        match = ROW.match(normalized.strip()) if re.search(r'\bscope\s*[123]\b',normalized,re.I) and 'co2' in normalized.lower() else None
        if not match and re.search(r'\bscope\s*[123]\b',normalized,re.I) and 'co2' in normalized.lower():
            match = ROW_LABELLED_UNIT.match(normalized.strip())
        scope = re.search(r'\bscope\s*([123])\b',match.group('label'),re.I) if match else None
        if match and re.search(r'\bscope\s*[123]\s*(?:and|&|\+|,)\s*[123]',match.group('label'),re.I):
            match = None
        if match and (not scope or len(re.findall(r'\bscope\s*[123]\b',match.group('label'),re.I)) != 1):
            match = None
        if not match:
            stripped = re.sub(r"\[\d+\]", '', line).strip()
            if header and stripped and not re.search(r"\d", stripped) and not re.search(r"\s{3,}", stripped):
                group = stripped.lstrip('# ').strip()
            continue
        if not header:
            warnings.append({"line": number, "code": "TABLE_MISSING_YEAR_HEADER"})
            continue
        hline, htext, years = header
        if len(years) < 2 or len(years) != len(set(years)) or (years != sorted(years) and years != sorted(years,reverse=True)):
            warnings.append({"line": number, "code": "AMBIGUOUS_MULTI_ENTITY_YEAR_HEADER"})
            continue
        tail = match.group('cells').strip()
        cells = re.split(r'\s+',tail)
        if len(cells) != len(years) or not all(CELL.fullmatch(c) for c in cells):
            warnings.append({"line": number, "code": "TABLE_COLUMN_MISMATCH"})
            continue
        for year, cell in zip(years, cells):
            missing = cell.lower() in {'n/a', '-', '–'}
            value = None if missing else float(re.sub(r"\[\d+\]", '', cell).replace(',', ''))
            if value is not None:
                value *= unit_multiplier(match.group('unit'))
            rows.append({"line": number, "header_line": hline, "header_quote": htext.strip(),
                         "quote": line.strip(), "section_hint": group,
                         "metric": 'scope' + scope.group(1), "year": year,
                         "value": value, "unit": 'tCO2e', "raw_cell": cell})
    return rows, warnings


def claim_segments(text):
    """Split large horizontal gaps; never join neighbouring columns as one claim."""
    if re.search(r"Content Index for Sustainability Reporting|^\s*CONTENTS\s*$", text, re.I | re.M):
        return
    for number, line in enumerate(text.splitlines(), 1):
        if re.search(r"Sustainability Report\s+20\d{2}", line, re.I):
            continue
        for segment in re.split(r"\s{5,}", line.strip()):
            # Drop page references, short titles and numeric table rows.
            if re.search(r"\s\d{1,3}\s*$", segment) or len(segment.split()) < 8:
                continue
            yield number, segment
