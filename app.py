import pandas as pd
import streamlit as st

from listingsfinder.config import EXPORT_DIR, GOOGLE_SHEET_URL, SCRAPEDO_TOKEN, SERPER_API_KEY
from listingsfinder.maintenance import check_source_health
from listingsfinder.pipeline import active_sources, run_search
from listingsfinder.sheets import append_rows, authorize_oauth, ensure_workbook, export_csv
from listingsfinder.store import get_sources, init_db, list_listings, list_runs, save_source

st.set_page_config(page_title="ListingsFinder AI", page_icon="LF", layout="wide")
init_db()

st.title("ListingsFinder AI")
st.caption("Dealio listing discovery, aggregation, deduplication, and manual review export. No enrichment, scoring, or outreach.")

with st.sidebar:
    st.subheader("System Status")
    st.write("Serper search:", "Configured" if SERPER_API_KEY else "Missing")
    st.write("Scrape.do fallback:", "Configured" if SCRAPEDO_TOKEN else "Optional / missing")
    st.link_button("Open Google Sheet", GOOGLE_SHEET_URL)
    if st.button("Authorize Google OAuth"):
        ok, msg = authorize_oauth()
        (st.success if ok else st.warning)(msg)
    if st.button("Prepare Google Sheet Tabs"):
        ok, msg = ensure_workbook()
        (st.success if ok else st.warning)(msg)
    if st.button("Sync Sources From Sheet"):
        sources, origin = active_sources()
        st.success(f"Loaded {len(sources)} sources from {origin}")

tabs = st.tabs(["Run Search", "Deal Sources", "Local Results", "Source Discovery", "Maintenance", "Rules"])

with tabs[0]:
    st.subheader("Advisor Mandate")
    mandate = st.text_input("Mandate", value="Find plumbing companies in Toronto")
    c1, c2, c3, c4 = st.columns(4)
    max_queries = c1.slider("Max Google queries", 1, 50, 18)
    results_per_query = c2.slider("Results per query", 1, 20, 10)
    scrape_pages = c3.toggle("Scrape result pages", value=True)
    discover_sources = c4.toggle("Find new sources", value=True)
    write_sheets = st.toggle("Write to Google Sheets when credentials are available", value=True)

    if st.button("Run Listings Search", type="primary"):
        with st.spinner("Searching sources, scraping pages, deduplicating, and exporting..."):
            criteria, queries, listings, duplicates, potential_sources, run, sheet_results, csv_paths = run_search(
                mandate,
                max_queries=max_queries,
                results_per_query=results_per_query,
                scrape_pages=scrape_pages,
                discover_sources=discover_sources,
                write_sheets=write_sheets,
            )

        st.success(f"Done: {len(listings)} unique listings, {len(duplicates)} duplicates removed, {len(potential_sources)} potential new sources.")
        st.write("Parsed criteria", criteria.__dict__)
        st.write("Queries used", queries)

        rows = [listing.to_dict() for listing in listings]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        with st.expander("Export results"):
            st.write(csv_paths)
            if sheet_results:
                st.dataframe(pd.DataFrame(sheet_results), use_container_width=True)

with tabs[1]:
    st.subheader("Deal Sources Registry")
    sources, origin = active_sources()
    st.caption(f"Current source registry: {origin}")
    edited = st.data_editor(pd.DataFrame(sources), use_container_width=True, num_rows="dynamic")
    c1, c2 = st.columns(2)
    if c1.button("Save Sources Locally"):
        for row in edited.fillna("").to_dict(orient="records"):
            if row.get("Source Name"):
                save_source(row)
        st.success("Sources saved locally")
    if c2.button("Export Sources to Google Sheet"):
        ok, msg = append_rows("Deal Sources", edited.fillna("").to_dict(orient="records"))
        (st.success if ok else st.warning)(msg)

with tabs[2]:
    st.subheader("Local Results")
    st.caption(f"CSV exports folder: {EXPORT_DIR}")
    listings = list_listings()
    runs = list_runs()
    c1, c2 = st.columns(2)
    with c1:
        st.write("Recent runs")
        run_rows = [row.get("run", row) for row in runs]
        st.dataframe(pd.DataFrame(run_rows), use_container_width=True)
    with c2:
        st.write("Stored listings")
        st.dataframe(pd.DataFrame(listings), use_container_width=True)

with tabs[3]:
    st.subheader("Potential New Sources")
    st.caption("Run a search with source discovery enabled to populate this tab in Google Sheets and CSV exports.")
    runs = list_runs()
    rows = []
    for row in runs:
        csv_paths = row.get("csv_paths", {})
        if csv_paths.get("Potential New Sources"):
            rows.append({"Run ID": row.get("run", {}).get("Run ID"), "CSV": csv_paths["Potential New Sources"]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

with tabs[4]:
    st.subheader("Source Registry Maintenance")
    sources = get_sources()
    limit = st.slider("Sources to check", 1, max(1, len(sources)), min(10, len(sources)))
    if st.button("Check Source Health"):
        with st.spinner("Checking source homepages..."):
            health_rows = check_source_health(sources[:limit])
        st.dataframe(pd.DataFrame(health_rows), use_container_width=True)
        path = export_csv("source_health_latest", health_rows, EXPORT_DIR)
        st.info(f"Saved CSV: {path}")

with tabs[5]:
    st.subheader("Scope Rules")
    st.markdown(
        """
- Find business-for-sale listings.
- Search approved sources plus Google.
- Scrape listing pages when available.
- Deduplicate by URL, contact details, company/city, title, and asking price.
- Export Listings, Mandates, Search Runs, Duplicates, and Potential New Sources.
- Do not score listings.
- Do not estimate missing values.
- Do not enrich companies or find owner emails.
- Do not write outreach or automate CRM actions.
"""
    )
