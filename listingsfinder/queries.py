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


# Major cities per province/state so one mandate fans out into many distinct
# searches -- the search engine then surfaces different individual listings
# instead of returning the same marketplace links for every near-identical query.
REGION_CITIES = {
    "ontario": ["Toronto", "Ottawa", "Mississauga", "Hamilton", "London", "Kitchener", "Windsor"],
    "british columbia": ["Vancouver", "Surrey", "Victoria", "Burnaby", "Kelowna"],
    "alberta": ["Calgary", "Edmonton", "Red Deer"],
    "quebec": ["Montreal", "Quebec City", "Laval", "Gatineau"],
    "manitoba": ["Winnipeg"],
    "saskatchewan": ["Saskatoon", "Regina"],
    "nova scotia": ["Halifax"],
    "new brunswick": ["Moncton", "Fredericton"],
}
REGION_COUNTRY = {region: "Canada" for region in REGION_CITIES}


def _expand_locations(location):
    loc = (location or "").strip()
    if not loc:
        return [""]
    key = loc.lower()
    locations = [loc]
    for region, cities in REGION_CITIES.items():
        if region in key or key in region:
            locations += cities
            country = REGION_COUNTRY.get(region)
            if country and country.lower() not in key:
                locations.append(country)
            break
    deduped = []
    for item in locations:
        if item not in deduped:
            deduped.append(item)
    return deduped


def generate_queries(criteria, sources=None):
    industry = (criteria.industry or criteria.keywords or criteria.original_query).strip()
    location = (criteria.location or "").strip()
    keywords = (criteria.keywords or "").strip()
    locations = _expand_locations(location)

    out = []
    search_terms = []
    for term in [industry, keywords]:
        term = term.strip()
        if term and term not in search_terms:
            search_terms.append(term)
    if not search_terms:
        search_terms = [criteria.original_query.strip()]

    # Template-outer, location-inner ordering: the first N queries (N = the
    # caller's max_queries cap) span many different cities rather than many
    # synonyms of the same city, maximizing distinct listings discovered.
    templates = [
        "{term} business for sale {loc}",
        "{term} company for sale {loc}",
        "{term} businesses for sale {loc}",
        "{term} business for sale {loc} asking price",
        "buy {term} business {loc}",
        "{term} business opportunity {loc}",
    ]
    for template in templates:
        for loc in locations:
            for term in search_terms:
                out.append(re.sub(r"\s+", " ", template.format(term=term, loc=loc)).strip())
    if criteria.price_max:
        out.append(f"{industry} business for sale {location} under {int(criteria.price_max)}".strip())
    if criteria.revenue_min:
        out.append(f"{industry} business for sale {location} revenue over {int(criteria.revenue_min)}".strip())

    for source in sources or []:
        if _active(source) and source.get("Website") and _source_matches_industry(source, industry):
            domain = source["Website"].replace("https://", "").replace("http://", "").split("/")[0]
            for term in search_terms:
                out.append(f"site:{domain} {term} {location} business for sale".strip())
                out.append(f"site:{domain} {term} {location} businesses for sale".strip())
                out.append(f"site:{domain} {term} {location} business opportunity".strip())
                out.append(f"site:{domain} {term} {location} asking price".strip())
                out.append(f"site:{domain} {term} {location} listings".strip())

    seen = []
    for query in out:
        if query and query not in seen:
            seen.append(query)
    return seen[:50]
