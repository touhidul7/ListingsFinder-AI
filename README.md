# ListingsFinder AI

Dealio listing discovery, aggregation, deduplication, scheduled mandate runs, Google Sheets export, and API access for other apps/automations.

The system does not score listings, estimate missing values, enrich companies, find owner emails, write outreach, or automate CRM work.

## What It Does

- Parses advisor mandates such as `Find plumbing businesses for sale in USA`.
- Generates search queries for Google/web search and active source domains.
- Uses free Python-scraped search with optional Serper fallback.
- Scrapes listing pages with optional Scrape.do fallback.
- Expands directory/search pages into actual listing pages where possible.
- Filters broad directory pages so they are not exported as listings.
- Deduplicates listings and assigns master listing IDs.
- Writes to Google Sheets tabs: `Deal Sources`, `Mandates`, `Listings`, `Search Runs`, `Potential New Sources`, and `Duplicates`.
- Runs scheduled mandates automatically from the Google Sheet.
- Exposes an HTTP API for search and scheduler execution.

## Local Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
streamlit run app.py
```

Or on Windows, double-click:

```text
run_app.bat
```

Then open:

```text
http://127.0.0.1:8501
```

## Environment Variables

Use `.env` locally, Coolify environment variables in Coolify, or server environment variables on a VPS.

Required for Google Sheets OAuth:

```text
GOOGLE_SHEET_URL=
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_TOKEN_INFO=
```

For `GOOGLE_OAUTH_TOKEN_INFO`, paste the full JSON content from `credentials/oauth_token.json` as one environment variable value. In Docker/Coolify, prefer `GOOGLE_OAUTH_TOKEN_INFO` over `GOOGLE_OAUTH_TOKEN_JSON=credentials/oauth_token.json`, because the local file path may not exist inside the container.

Optional search/scrape providers:

```text
SEARCH_PROVIDER=auto
SERPER_API_KEY=
SCRAPEDO_TOKEN=
```

Optional AI mandate parser:

```text
AI_PROVIDER=Rule-based
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
OPENROUTER_API_KEY=
OPENROUTER_MODEL=anthropic/claude-sonnet-4.5
```

API and scheduler:

```text
LISTINGSFINDER_API_KEY=choose-a-long-random-secret
SCHEDULER_POLL_SECONDS=300
SCHEDULE_MAX_QUERIES=18
SCHEDULE_RESULTS_PER_QUERY=10
SCHEDULE_SCRAPE_PAGES=true
SCHEDULE_DISCOVER_SOURCES=false
DIRECTORY_MAX_LINKS_PER_PAGE=25
DIRECTORY_MAX_PAGES=10
```

Email notifications with Resend:

```text
RESEND_API_KEY=
RESEND_FROM_EMAIL=ListingsFinder <notifications@yourdomain.com>
```

## Google Sheet Setup

The workbook should contain these tabs. The app can prepare them from the sidebar using `Prepare Google Sheet Tabs`.

```text
Deal Sources
Mandates
Listings
Search Runs
Potential New Sources
Duplicates
```

Link-edit access is not enough for API writing. The Google account represented by OAuth or service account credentials must have access to the sheet.

## AI Settings

The app can run in `Rule-based` mode with no AI key. AI is only used to convert the advisor search input into structured criteria. Search, scraping, deduplication, exports, and run logging remain rule-based.

In the Streamlit `AI Settings` tab, users can select:

```text
Rule-based
Anthropic
OpenRouter
```

Keys entered in the UI are masked. They are saved only if the remember option is checked.

## Scheduled Mandates

The scheduler reads the `Mandates` tab and runs due rows automatically.

For a one-time mandate:

```text
Original Query: Pharmacies for sale in Ontario
Frequency: One-time
Status: Active
Last Run: leave blank
Next Run: leave blank, or set a past/current date-time
Notify Email: optional email address
```

After it runs, the app sets `Last Run` and changes `Status` to `Completed`, so it will not run again.

For recurring mandates:

```text
Frequency: Daily, Weekly, or Monthly
Status: Active
Last Run: leave blank for first run
Next Run: optional first run time
Notify Email: optional email address
```

Recurring mandates run when due, then the app sets the next run to 5 AM Eastern.

Use one of these statuses to stop a mandate:

```text
Inactive
Paused
Disabled
Completed
Done
```

The scheduler loop checks the sheet every `SCHEDULER_POLL_SECONDS`. Recommended production value:

```text
SCHEDULER_POLL_SECONDS=300
```

That means it checks every 5 minutes, but only runs mandates that are due.

## API

The API runs with:

```bash
uvicorn listingsfinder.api:app --host 0.0.0.0 --port 8000
```

If `LISTINGSFINDER_API_KEY` is set, pass it as either:

```text
X-API-Key: your-key
```

or:

```text
Authorization: Bearer your-key
```

### Health Check

```http
GET /health
```

Example:

```bash
curl https://YOUR_API_DOMAIN/health
```

Response:

```json
{"ok":true,"service":"ListingsFinder API"}
```

### POST Search

```http
POST /api/search
```

Example:

```bash
curl -X POST https://YOUR_API_DOMAIN/api/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_LISTINGSFINDER_API_KEY" \
  -d '{"mandate":"Find plumbing businesses for sale in USA","max_queries":18,"results_per_query":10,"scrape_pages":true,"discover_sources":false,"write_sheets":true}'
```

Body fields:

```json
{
  "mandate": "Find plumbing businesses for sale in USA",
  "max_queries": 18,
  "results_per_query": 10,
  "scrape_pages": true,
  "discover_sources": false,
  "write_sheets": true,
  "ai_provider": "Rule-based",
  "ai_model": "",
  "ai_api_key": "",
  "mandate_id": "",
  "frequency": "One-time"
}
```

The response includes parsed criteria, queries used, run summary, listings, duplicates, potential sources, sheet export status, and CSV paths.

### GET Search

```http
GET /api/search?mandate=Find%20plumbing%20businesses%20for%20sale%20in%20USA
```

Example:

```bash
curl "https://YOUR_API_DOMAIN/api/search?mandate=Find%20plumbing%20businesses%20for%20sale%20in%20USA&max_queries=18&results_per_query=10&scrape_pages=true&write_sheets=true" \
  -H "X-API-Key: YOUR_LISTINGSFINDER_API_KEY"
```

### Run Scheduled Mandates

```http
POST /api/scheduler/run
```

Example:

```bash
curl -X POST https://YOUR_API_DOMAIN/api/scheduler/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_LISTINGSFINDER_API_KEY" \
  -d '{"force":false}'
```

Use `force:true` only for testing. It ignores `Next Run`.

## Coolify Deployment

This repo supports Coolify from GitHub using `docker-compose.yml`.

Coolify starts three services:

```text
ui        Streamlit dashboard, internal port 8501
api       HTTP API, internal port 8000
scheduler Background mandate polling worker, no public port
```

Setup:

1. Connect the GitHub repository in Coolify.
2. Choose Docker Compose deployment.
3. Set base directory to `/`.
4. Set Docker Compose location to `/docker-compose.yml`.
5. Add environment variables in Coolify, not in the repo.
6. Deploy.

Routing:

```text
ui -> internal port 8501
api -> internal port 8000, only if public API is needed
scheduler -> no domain
```

The compose file uses `expose`, not fixed host `ports`, so it does not conflict with host ports already used on the VPS.

If the UI shows a Streamlit chunk error such as:

```text
Failed to fetch dynamically imported module: /static/js/Spinner...
```

Try:

1. Hard refresh with `Ctrl+F5` or use an incognito window.
2. Confirm the `ui` domain routes to internal port `8501`.
3. Confirm the `api` domain routes to internal port `8000`.
4. Confirm no domain is routed to `scheduler`.
5. Redeploy after pushing the latest Docker/Compose changes.

## VPS Deployment

Run the three processes directly:

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
uvicorn listingsfinder.api:app --host 0.0.0.0 --port 8000
python -m listingsfinder.scheduler_service
```

Or use the included systemd unit templates:

```text
deploy/systemd/listingsfinder-ui.service
deploy/systemd/listingsfinder-api.service
deploy/systemd/listingsfinder-scheduler.service
```

Install on the VPS:

```bash
sudo cp deploy/systemd/listingsfinder-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable listingsfinder-ui listingsfinder-api listingsfinder-scheduler
sudo systemctl start listingsfinder-ui listingsfinder-api listingsfinder-scheduler
sudo systemctl status listingsfinder-ui listingsfinder-api listingsfinder-scheduler
```

If your app folder or virtualenv lives somewhere else, update `WorkingDirectory` and `ExecStart` inside the service files before enabling them.

## GitHub Actions Scheduler

GitHub Actions was used earlier for scheduled mandates. If the app is now deployed on Coolify/VPS, disable the GitHub workflow to avoid duplicate runs.

Disable from GitHub:

```text
GitHub repo -> Actions -> Run scheduled mandates -> three dots -> Disable workflow
```

The workflow file is:

```text
.github/workflows/scheduled-mandates.yml
```

## Troubleshooting

API works but UI bad gateway:

```text
Route ui domain to internal port 8501.
```

API health check:

```bash
curl https://YOUR_API_DOMAIN/health
```

Scheduler is running if logs show:

```text
ListingsFinder scheduler loop started
```

Manual search finds results but scheduled search finds zero:

```text
Set SCHEDULE_MAX_QUERIES=18
Set SCHEDULE_RESULTS_PER_QUERY=10
Set SCHEDULE_SCRAPE_PAGES=true
```

One-time mandate did not run again:

```text
Status=Active
Frequency=One-time
Last Run=
Next Run=
```

Then wait up to `SCHEDULER_POLL_SECONDS`.