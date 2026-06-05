import re


def _active(source):
    value = str(source.get("Active", "TRUE")).strip().lower()
    return value in ("", "true", "yes", "1", "active", "y")


GENERAL_FOCUS = {"", "general", "general m&a", "m&a", "business", "businesses", "marketplace", "all"}


def _tokens(value):
    return {w for w in re.split(r"[^a-z0-9]+", (value or "").lower()) if len(w) > 2}


def _source_matches_industry(source, industry):
    focus = str(source.get("Industry Focus", "") or "").strip().lower()
    industry_low = (industry or "").strip().lower()
    if focus in GENERAL_FOCUS:
        return True
    if not industry_low:
        return True

    focus_words = _tokens(focus)
    industry_words = _tokens(industry_low)
    return bool(focus_words & industry_words)


def generate_queries(criteria, sources=None):
    industry = (criteria.industry or criteria.keywords or criteria.original_query).strip()
    location = (criteria.location or "").strip()
    keywords = (criteria.keywords or "").strip()
    locations = [location] if location else [""]

    out = []
    search_terms = []
    for term in [industry, keywords]:
        term = term.strip()
        if term and term not in search_terms:
            search_terms.append(term)
    if not search_terms:
        search_terms = [criteria.original_query.strip()]
    for loc in locations:
        for term in search_terms:
            out += [
                f"{term} business for sale {loc}".strip(),
                f"{term} company for sale {loc}".strip(),
                f"{term} listings for sale {loc}".strip(),
                f"{term} broker {loc}".strip(),
                f"{term} acquisition opportunity {loc}".strip(),
            ]
    if criteria.price_max:
        out.append(f"{industry} business for sale {location} under {int(criteria.price_max)}".strip())
    if criteria.revenue_min:
        out.append(f"{industry} business for sale {location} revenue over {int(criteria.revenue_min)}".strip())

    for source in sources or []:
        if _active(source) and source.get("Website") and _source_matches_industry(source, industry):
            domain = source["Website"].replace("https://", "").replace("http://", "").split("/")[0]
            for term in search_terms:
                out.append(f"site:{domain} {term} {location} business for sale".strip())
                out.append(f"site:{domain} {term} {location} listings".strip())

    seen = []
    for query in out:
        if query and query not in seen:
            seen.append(query)
    return seen[:50]
