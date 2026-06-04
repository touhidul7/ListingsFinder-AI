import os
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
DEFAULT_SHEET_URL='https://docs.google.com/spreadsheets/d/19wCuVx76pZm3RG9MgH0BW-BI390YYjD9PMWq-UKFF1A/edit?usp=sharing'
SERPER_API_KEY=os.getenv('SERPER_API_KEY','').strip()
SCRAPEDO_TOKEN=os.getenv('SCRAPEDO_TOKEN','').strip()
GOOGLE_SHEET_URL=os.getenv('GOOGLE_SHEET_URL',DEFAULT_SHEET_URL).strip()
GOOGLE_SERVICE_ACCOUNT_JSON=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON','credentials/service_account.json').strip()
GOOGLE_OAUTH_CLIENT_ID=os.getenv('GOOGLE_OAUTH_CLIENT_ID','').strip()
GOOGLE_OAUTH_CLIENT_SECRET=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET','').strip()
GOOGLE_OAUTH_TOKEN_JSON=os.getenv('GOOGLE_OAUTH_TOKEN_JSON','credentials/oauth_token.json').strip()
GOOGLE_OAUTH_REDIRECT_PORT=int(os.getenv('GOOGLE_OAUTH_REDIRECT_PORT','8502').strip() or '8502')
DATA_DIR=ROOT/'data'; EXPORT_DIR=ROOT/'exports'; DB_PATH=DATA_DIR/'listingsfinder.db'
for p in (DATA_DIR,EXPORT_DIR,ROOT/'credentials'): p.mkdir(exist_ok=True)
