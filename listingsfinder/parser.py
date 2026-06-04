import re

from .models import SearchCriteria

HINTS = [
    "plumbing",
    "hvac",
    "dental",
    "clinic",
    "accounting",
    "car wash",
    "landscaping",
    "roofing",
    "restaurant",
    "manufacturing",
    "saas",
    "agency",
    "childcare",
    "pharmacy",
    "clothing",
    "apparel",
]


def money(text):
    text = (text or "").replace(",", "")
    m = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(m|k|mm|million|thousand)?", text, re.I)
    if not m:
        return None
    number = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("m", "mm", "million"):
        return number * 1_000_000
    if unit in ("k", "thousand"):
        return number * 1_000
    return number


def _range_value(patterns, query):
    for pattern in patterns:
        m = re.search(pattern, query, re.I)
        if m:
            return money(m.group(0))
    return None


def clean_industry(value):
    value = (value or "").strip()
    value = re.sub(r"\bcopany\b", "company", value, flags=re.I)
    value = re.sub(r"\b(?:please|find|search for|look for|looking for|best|a|an|the)\b", " ", value, flags=re.I)
    value = re.sub(r"\b(?:companies|company|businesses|business|for sale|acquisition|opportunities?)\b", " ", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" -,.")
    value = value.title()
    value = re.sub(r"\bHvac\b", "HVAC", value)
    value = re.sub(r"\bSaas\b", "SaaS", value)
    return value


def parse_mandate(query):
    q = (query or "").strip()
    low = q.lower()
    industry = next((h.title() for h in HINTS if h in low), "")

    if not industry:
        m = re.search(
            r"(?:find|search for)?\s*(.+?)\s+(?:companies|businesses|clinics|firms|practices|for sale|in\b)",
            low,
            re.I,
        )
        industry = clean_industry(m.group(1)) if m else ""

    m = re.search(
        r"\b(?:in|near|around)\s+([a-zA-Z .'-]+?)(?:\s+(?:under|below|over|above|min|max|with|for sale)\b|$)",
        q,
        re.I,
    )
    location = m.group(1).strip().rstrip(".,").title() if m else ""

    price_max = _range_value([r"(?:under|below|less than|max(?:imum)?|up to)\s*\$?\s*[0-9][0-9.,]*\s*(?:m|k|mm|million|thousand)?"], low)
    price_min = _range_value([r"(?:over|above|more than|min(?:imum)?|at least)\s*\$?\s*[0-9][0-9.,]*\s*(?:m|k|mm|million|thousand)?"], low)
    revenue_min = _range_value([r"(?:revenue|sales)\s*(?:over|above|more than|min(?:imum)?|at least)\s*\$?\s*[0-9][0-9.,]*\s*(?:m|k|mm|million|thousand)?"], low)
    revenue_max = _range_value([r"(?:revenue|sales)\s*(?:under|below|less than|max(?:imum)?|up to)\s*\$?\s*[0-9][0-9.,]*\s*(?:m|k|mm|million|thousand)?"], low)

    exclude = ""
    m = re.search(r"\b(?:exclude|not)\s+(.+)$", q, re.I)
    if m:
        exclude = m.group(1).strip()

    return SearchCriteria(
        original_query=q,
        industry=clean_industry(industry),
        location=location,
        price_min=price_min,
        price_max=price_max,
        revenue_min=revenue_min,
        revenue_max=revenue_max,
        keywords=industry,
        exclude=exclude,
    )
