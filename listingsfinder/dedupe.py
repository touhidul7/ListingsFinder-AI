import re
from datetime import datetime, timezone

from rapidfuzz import fuzz


def _norm(value):
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _city(value):
    return _norm(value).split(",")[0]


def _money_number(value):
    if not value:
        return None
    text = value.replace(",", "").lower()
    m = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(m|mm|million|k|thousand)?", text)
    if not m:
        return None
    amount = float(m.group(1))
    unit = m.group(2) or ""
    if unit in ("m", "mm", "million"):
        return amount * 1_000_000
    if unit in ("k", "thousand"):
        return amount * 1_000
    return amount


def _near_price(a, b):
    av = _money_number(a)
    bv = _money_number(b)
    if av is None or bv is None:
        return False
    return abs(av - bv) <= max(10_000, min(av, bv) * 0.05)


def dedupe_listings(listings):
    masters = []
    dups = []
    found_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for listing in listings:
        match = None
        reason = ""
        match_type = ""
        for master in masters:
            if listing.source_url and listing.source_url == master.source_url:
                match, reason, match_type = master, "Same URL", "Exact"
                break
            if listing.contact_email and _norm(listing.contact_email) == _norm(master.contact_email):
                match, reason, match_type = master, "Same email", "Exact"
                break
            if listing.contact_phone and _norm(listing.contact_phone) == _norm(master.contact_phone):
                match, reason, match_type = master, "Same phone", "Exact"
                break
            if listing.company_name and master.company_name and _norm(listing.company_name) == _norm(master.company_name) and _city(listing.location) == _city(master.location):
                match, reason, match_type = master, "Same company name and city", "Strong"
                break
            score = fuzz.token_set_ratio((listing.company_name or listing.listing_title), (master.company_name or master.listing_title))
            if score >= 88 and (_city(listing.location) == _city(master.location) or not listing.location or not master.location):
                match, reason, match_type = master, f"Similar title/name score {score}", "Strong"
                break
            title_score = fuzz.token_set_ratio(listing.listing_title, master.listing_title)
            if title_score >= 78 and _near_price(listing.asking_price, master.asking_price):
                match, reason, match_type = master, f"Similar title and asking price score {title_score}", "Medium"
                break
        if match:
            dups.append(
                {
                    "Master Listing ID": match.master_listing_id,
                    "Duplicate Listing ID": listing.listing_id,
                    "Duplicate Source": listing.source,
                    "Duplicate URL": listing.source_url,
                    "Match Type": match_type,
                    "Reason": reason,
                    "Date Found": found_at,
                }
            )
        else:
            listing.master_listing_id = f"DEALIO-{len(masters) + 1:05d}"
            masters.append(listing)
    return masters, dups
