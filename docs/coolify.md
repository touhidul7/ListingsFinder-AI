# Coolify Deployment

Yes, this app can be deployed through Coolify from GitHub.

## What Coolify Uses

Use the repo root `docker-compose.yml`.

It starts three containers:

- `ui` for Streamlit
- `api` for the HTTP API
- `scheduler` for automatic mandate polling

## Setup Steps

1. Connect your GitHub repository in Coolify.
2. Choose Docker Compose deployment.
3. Point Coolify at the repo root `docker-compose.yml`.
4. Add the required environment variables in Coolify, not in the repo.
5. Deploy.

## Environment Variables

Add the same variables you would normally put in `.env`, especially:

```text
GOOGLE_SHEET_URL
GOOGLE_OAUTH_CLIENT_ID
GOOGLE_OAUTH_CLIENT_SECRET
GOOGLE_OAUTH_TOKEN_JSON
RESEND_API_KEY
RESEND_FROM_EMAIL
LISTINGSFINDER_API_KEY
SERPER_API_KEY
SCRAPEDO_TOKEN
AI_PROVIDER
ANTHROPIC_API_KEY
ANTHROPIC_MODEL
OPENROUTER_API_KEY
OPENROUTER_MODEL
SCHEDULER_POLL_SECONDS
SCHEDULE_MAX_QUERIES
SCHEDULE_RESULTS_PER_QUERY
SCHEDULE_SCRAPE_PAGES
SCHEDULE_DISCOVER_SOURCES
```

## Notes

- Coolify can auto-deploy on GitHub pushes.
- The scheduler runs continuously inside its own container, so mandates are checked automatically.
- The API returns the collected listings after the search finishes.
- In Coolify, route the `ui` service to internal port `8501`.
- If you want the API publicly reachable, route the `api` service to internal port `8000` or give it its own domain/subdomain.
- The compose file uses `expose` instead of fixed host `ports`, so it will not conflict with ports already used on the VPS.

## Quick Test

After deploy, check:

```text
/health
```

on the API container, and use the Streamlit dashboard to confirm Google Sheets access.