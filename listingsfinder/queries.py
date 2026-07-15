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
# NOTE: a city-level mandate ("Toronto", "New York") is NOT fanned out -- the
# user wants listings in that city only. Fan-out applies to region mandates.
REGION_CITIES = {
    "ontario": ["Toronto", "Ottawa", "Mississauga", "Hamilton", "London", "Kitchener", "Windsor"],
    "british columbia": ["Vancouver", "Surrey", "Victoria", "Burnaby", "Kelowna"],
    "alberta": ["Calgary", "Edmonton", "Red Deer"],
    "quebec": ["Montreal", "Quebec City", "Laval", "Gatineau"],
    "manitoba": ["Winnipeg"],
    "saskatchewan": ["Saskatoon", "Regina"],
    "nova scotia": ["Halifax"],
    "new brunswick": ["Moncton", "Fredericton"],
    "california": ["Los Angeles", "San Diego", "San Francisco", "San Jose", "Sacramento", "Fresno"],
    "texas": ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth"],
    "florida": ["Miami", "Orlando", "Tampa", "Jacksonville", "Fort Lauderdale"],
    "illinois": ["Chicago", "Naperville", "Rockford"],
    "arizona": ["Phoenix", "Tucson", "Scottsdale"],
    "georgia": ["Atlanta", "Savannah", "Augusta"],
    "washington": ["Seattle", "Spokane", "Tacoma"],
    "colorado": ["Denver", "Colorado Springs", "Boulder"],
    "michigan": ["Detroit", "Grand Rapids", "Ann Arbor"],
    "ohio": ["Columbus", "Cleveland", "Cincinnati"],
    "pennsylvania": ["Philadelphia", "Pittsburgh", "Allentown"],
    "north carolina": ["Charlotte", "Raleigh", "Durham"],
    "nevada": ["Las Vegas", "Reno"],
    "massachusetts": ["Boston", "Worcester", "Springfield"],
    "new jersey": ["Newark", "Jersey City", "Trenton"],
}
_CA_REGIONS = ("ontario", "british columbia", "alberta", "quebec", "manitoba", "saskatchewan", "nova scotia", "new brunswick")
REGION_COUNTRY = {region: ("Canada" if region in _CA_REGIONS else "United States") for region in REGION_CITIES}

_US_CITY_HINTS = {
    "new york", "nyc", "los angeles", "chicago", "houston", "miami", "dallas",
    "boston", "seattle", "san francisco", "san diego", "san jose", "atlanta",
    "phoenix", "philadelphia", "denver", "austin", "las vegas", "orlando",
    "tampa", "charlotte", "brooklyn", "manhattan", "detroit", "columbus",
}
_CA_CITY_HINTS = {
    "toronto", "vancouver", "montreal", "calgary", "ottawa", "edmonton",
    "winnipeg", "mississauga", "hamilton", "victoria", "halifax", "quebec city",
    "kitchener", "surrey", "burnaby", "kelowna", "gta", "windsor", "saskatoon",
    "regina", "moncton", "fredericton", "laval", "gatineau",
}

# Big national marketplaces. Serper `site:` queries against these return the
# individual listing URLs directly, which sidesteps their bot protection --
# their category pages are JS-rendered and cannot be crawled for children.
MARKETPLACE_DOMAINS = (
    "bizbuysell.com",
    "businessesforsale.com",
    "bizquest.com",
    "businessbroker.net",
    "dealstream.com",
)


def country_hint(location):
    """Best-effort 'us'/'ca' Google geo for the mandate location, or None."""
    key = (location or "").strip().lower()
    if not key:
        return None
    if "united states" in key or re.search(r"\busa?\b", key):
        return "us"
    if "canada" in key:
        return "ca"
    for region, country in REGION_COUNTRY.items():
        if region in key:
            return "us" if country == "United States" else "ca"
    first = key.split(",")[0].strip()
    if first in _US_CITY_HINTS:
        return "us"
    if first in _CA_CITY_HINTS:
        return "ca"
    return None


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
        "{term} business for sale {loc} cash flow",
        "established {term} business for sale {loc}",
        "{term} company acquisition opportunity {loc}",
        "{loc} {term} business listing for sale",
    ]
    blocks = []
    for template in templates:
        block = []
        for loc in locations:
            for term in search_terms:
                block.append(re.sub(r"\s+", " ", template.format(term=term, loc=loc)).strip())
        blocks.append(block)
    # Marketplace site: queries go right after the first generic block -- Serper
    # returns their individual listing URLs directly, which is the highest-
    # precision source of single listings.
    marketplace = []
    for domain in MARKETPLACE_DOMAINS:
        for loc in locations[:3]:
            for term in search_terms:
                marketplace.append(re.sub(r"\s+", " ", f"site:{domain} {term} business for sale {loc}").strip())
    out.extend(blocks[0])
    out.extend(marketplace)
    for block in blocks[1:]:
        out.extend(block)
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
    # Large pool on purpose: the pipeline walks this list incrementally and
    # keeps going past max_queries until it reaches its minimum listing count.
    return seen[:150]
