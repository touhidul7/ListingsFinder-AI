def _active(source):
    return str(source.get("Active", "TRUE")).strip().lower() in ("true", "yes", "1", "active", "y")


def generate_queries(criteria, sources=None):
    industry = (criteria.industry or criteria.keywords or criteria.original_query).strip()
    location = (criteria.location or "").strip()
    locations = [location] if location else [""]
    if location.lower() in ["toronto", "gta"]:
        locations += ["Ontario", "GTA"]
    if location.lower() in ["florida", "fl"]:
        locations += ["FL"]

    out = []
    for loc in locations:
        out += [
            f"{industry} business for sale {loc}".strip(),
            f"{industry} company for sale {loc}".strip(),
            f"{industry} acquisition {loc}".strip(),
            f"{industry} owner operator business {loc}".strip(),
        ]
    if criteria.price_max:
        out.append(f"{industry} business for sale {location} under {int(criteria.price_max)}".strip())
    if criteria.revenue_min:
        out.append(f"{industry} business for sale {location} revenue over {int(criteria.revenue_min)}".strip())

    for source in sources or []:
        if _active(source) and source.get("Website"):
            domain = source["Website"].replace("https://", "").replace("http://", "").split("/")[0]
            out.append(f"site:{domain} {industry} {location} business for sale".strip())
            out.append(f"site:{domain} {industry} {location}".strip())

    seen = []
    for query in out:
        if query and query not in seen:
            seen.append(query)
    return seen[:50]
