# ListingsFinder AI

Dealio listing discovery, aggregation, deduplication, and manual-review export. The system does not score listings, estimate missing values, enrich companies, find owner emails, write outreach, or automate CRM work.

## Run

Double-click `run_app.bat`, then open:

http://127.0.0.1:8501

The app includes:

- Mandate parser: `Find plumbing companies in Toronto`
- Query generation for Google and active source domains
- Free Python-scraped web search with optional Serper fallback
- Direct scrape with Scrape.do fallback
- Deduplication with master listing IDs
- Local SQLite storage
- CSV exports in `exports/`
- Google Sheets tabs for Deal Sources, Mandates, Listings, Search Runs, Potential New Sources, and Duplicates when API credentials are available
- Source health checks for registry maintenance
- Optional AI mandate parser through Anthropic or OpenRouter

## Google Sheet

https://docs.google.com/spreadsheets/d/19wCuVx76pZm3RG9MgH0BW-BI390YYjD9PMWq-UKFF1A/edit

Link-edit access is not enough for Google Sheets API writing. Put a service account JSON file at `credentials/service_account.json` and share the sheet with the service-account email. Without credentials, the app still runs and exports CSV files in `exports/`.

## AI Settings

The app can run in `Rule-based` mode with no AI key. For better natural-language mandate parsing, add one of these providers in `.env` locally or Streamlit Secrets in deployment:

```text
AI_PROVIDER=Rule-based
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
OPENROUTER_API_KEY=
OPENROUTER_MODEL=anthropic/claude-sonnet-4.5
```

AI is only used to convert the advisor's search input into structured criteria. Search, scraping, deduplication, exports, and run logging remain rule-based.

The AI Settings tab also accepts masked API keys for the current app session. Keys entered in the UI are not written to `.env`, the local database, CSV exports, or Google Sheets.

## Scheduled Mandates

The Mandates sheet supports `Frequency`, `Last Run`, `Next Run`, and `Notify Email` columns. To run recurring mandates automatically, schedule this command on the host at 5 AM Eastern:

```text
run_scheduled.bat
```

The scheduler reads due mandates from Google Sheets, runs the search, appends new results, updates `Last Run` / `Next Run`, and sends an email summary when SMTP settings are configured.

Inside Streamlit, the `Automation` tab can manually run due mandates and show automation status. Streamlit does not run background jobs by itself while idle, so fully automatic 5 AM Eastern execution still needs an external trigger such as GitHub Actions, a VPS cron job, Windows Task Scheduler, or another hosted scheduler.

For GitHub Actions setup, see:

```text
docs/github-actions-scheduler.md
```

For VPS deployment with the app UI, API, and automatic mandate loop, see:

```text
docs/vps-deployment.md
```

For email notifications, Resend is supported:

```text
RESEND_API_KEY=
RESEND_FROM_EMAIL=ListingsFinder <verified@yourdomain.com>
```
