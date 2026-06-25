import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from .ai_parser import parse_mandate_with_ai
from .queries import generate_queries
from .search import web_search
from .scraper import expand_directory_results, is_listing_page, scrape_result
from .dedupe import dedupe_listings
from .store import get_sources, replace_sources, save_run, save_listings
from .sheets import append_rows, export_csv, read_deal_sources
from .config import DIRECTORY_MAX_LINKS_PER_PAGE, DIRECTORY_MAX_PAGES, EXPORT_DIR
from .models import Listing, now_iso


def active_sources():
    sheet_sources, err = read_deal_sources()
    if sheet_sources:
        replace_sources(sheet_sources)
        return sheet_sources, "Google Sheet"
    return get_sources(), f"Local registry ({err})" if err else "Local registry"


def _listing_rows(listings, mandate_id=""):
    return [
        {
            "Master Listing ID": l.master_listing_id,
            "Listing ID": l.listing_id,
            "Source": l.source,
            "Source URL": l.source_url,
            "Listing Title": l.listing_title,
            "Company Name": l.company_name,
            "Industry": l.industry,
            "Location": l.location,
            "Asking Price": l.asking_price,
            "Revenue": l.revenue,
            "Cash Flow": l.cash_flow,
            "EBITDA": l.ebitda,
            "Description": l.description,
            "Contact Name": l.contact_name,
            "Contact Email": l.contact_email,
            "Contact Phone": l.contact_phone,
            "Listing Date": l.listing_date,
            "Scrape Date": l.scrape_date,
            "Status": l.status,
            "Notes": l.notes,
            "Mandate ID": mandate_id,
        }
        for l in listings
    ]


def _mandate_row(mandate_id, criteria, frequency="One-time"):
    return {
        "Mandate ID": mandate_id,
        "Date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "User": "Dealio Advisor",
        "Original Query": criteria.original_query,
        "Industry": criteria.industry,
        "Location": criteria.location,
        "Revenue Min": criteria.revenue_min or "",
        "Revenue Max": criteria.revenue_max or "",
        "Price Min": criteria.price_min or "",
        "Price Max": criteria.price_max or "",
        "Keywords": criteria.keywords,
        "Exclude": criteria.exclude,
        "Frequency": frequency,
        "Last Run": "",
        "Next Run": "",
        "Notify Email": "",
        "Status": "Searched",
        "Notes": "",
    }


def discover_new_sources(criteria, sources, max_results=10):
    known_domains = {
        (src.get("Website") or "").replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].lower()
        for src in sources
    }
    queries = [
        f"{criteria.industry} business broker {criteria.location}".strip(),
        f"{criteria.industry} businesses for sale {criteria.location} broker".strip(),
        f"{criteria.location} business brokers {criteria.industry}".strip(),
    ]
    rows = []
    seen = set()
    for query in queries:
        for result in web_search(query, num=max_results):
            url = result.get("url", "")
            domain = urlparse(url).netloc.replace("www.", "").lower()
            if not domain or domain in known_domains or domain in seen:
                continue
            seen.add(domain)
            rows.append(
                {
                    "Source Name": result.get("title", domain)[:120],
                    "Website": domain,
                    "Category": "Potential",
                    "Geography": criteria.location,
                    "Industry Focus": criteria.industry,
                    "Discovered From Query": query,
                    "Reason": result.get("snippet", "")[:300],
                    "Status": "Needs Review",
                    "Notes": url,
                }
            )
    return rows


def run_search(
    mandate,
    max_queries=30,
    results_per_query=10,
    scrape_pages=True,
    discover_sources=True,
    write_sheets=True,
    ai_provider="Rule-based",
    ai_model="",
    ai_api_key="",
    mandate_id="",
    log_mandate=True,
    frequency="One-time",
):
    mandate_id = mandate_id or "MAND-" + uuid.uuid4().hex[:8].upper()
    run_id = "RUN-" + uuid.uuid4().hex[:8].upper()
    try:
        criteria, parser_used = parse_mandate_with_ai(mandate, ai_provider, ai_model, ai_api_key)
        parser_note = f"mandate parser: {parser_used}"
    except Exception as exc:
        criteria, parser_used = parse_mandate_with_ai(mandate, "Rule-based", "")
        parser_note = f"mandate parser: Rule-based fallback; AI error: {exc}"
    sources, source_origin = active_sources()
    queries = generate_queries(criteria, sources)[:max_queries]
    raw = []
    for q in queries:
        try:
            raw.extend(web_search(q, num=results_per_query))
        except Exception as e:
            raw.append({"title": f"ERROR searching {q}", "url": "", "snippet": str(e), "query": q, "source": "error"})
    seen = set()
    filtered = []
    for r in raw:
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            filtered.append(r)
    filtered = expand_directory_results(filtered, criteria.industry, criteria.location, max_links_per_page=DIRECTORY_MAX_LINKS_PER_PAGE, max_directory_pages=DIRECTORY_MAX_PAGES)
    listings = []
    for r in filtered:
        if scrape_pages:
            try:
                listing = scrape_result(r, criteria.industry, criteria.location)
                if is_listing_page(listing, criteria.industry, criteria.location):
                    listings.append(listing)
            except Exception as e:
                fallback_listing = Listing(
                    source_url=r.get("url", ""),
                    listing_title=r.get("title", ""),
                    source=r.get("source", ""),
                    industry=criteria.industry,
                    location=criteria.location,
                    description=r.get("snippet", ""),
                    scrape_date=now_iso(),
                    notes=f"scrape_error={e}",
                )
                if is_listing_page(fallback_listing, criteria.industry, criteria.location):
                    listings.append(fallback_listing)
        else:
            listings.append(
                Listing(
                    source=r.get("source", ""),
                    source_url=r.get("url", ""),
                    listing_title=r.get("title", ""),
                    description=r.get("snippet", ""),
                    industry=criteria.industry,
                    location=criteria.location,
                    scrape_date=now_iso(),
                )
            )

    masters, duplicates = dedupe_listings(listings)
    potential_sources = discover_new_sources(criteria, sources) if discover_sources else []
    save_listings(masters)
    run = {
        "Run ID": run_id,
        "Mandate ID": mandate_id,
        "Date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "User": "Dealio Advisor",
        "Search Query": mandate,
        "Industry": criteria.industry,
        "Location": criteria.location,
        "Sources Searched": len(sources),
        "Listings Found": len(masters),
        "Duplicates Removed": len(duplicates),
        "New Sources Found": len(potential_sources),
        "Notes": f"Search + scrape pipeline; source registry: {source_origin}; {parser_note}",
    }
    rows = _listing_rows(masters, mandate_id)
    csv_paths = {
        "Listings": export_csv("listings_" + run_id, rows, EXPORT_DIR),
        "Duplicates": export_csv("duplicates_" + run_id, duplicates, EXPORT_DIR),
        "Potential New Sources": export_csv("potential_sources_" + run_id, potential_sources, EXPORT_DIR),
    }
    sheet_results = []
    if write_sheets:
        exports = [
            ("Listings", rows),
            ("Search Runs", [run]),
            ("Duplicates", duplicates),
            ("Potential New Sources", potential_sources),
        ]
        if log_mandate:
            exports.insert(0, ("Mandates", [_mandate_row(mandate_id, criteria, frequency)]))
        for tab, tab_rows in exports:
            ok, msg = append_rows(tab, tab_rows)
            sheet_results.append({"tab": tab, "ok": ok, "message": msg})
    save_run(
        run_id,
        {
            "criteria": criteria.__dict__,
            "queries": queries,
            "run": run,
            "sheet_results": sheet_results,
            "csv_paths": csv_paths,
        },
    )
    return criteria, queries, masters, duplicates, potential_sources, run, sheet_results, csv_paths
