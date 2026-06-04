import os
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
DEFAULT_SHEET_URL='https://docs.google.com/spreadsheets/d/19wCuVx76pZm3RG9MgH0BW-BI390YYjD9PMWq-UKFF1A/edit?usp=sharing'


def setting(name, default=""):
    value = os.getenv(name)
    if value not in (None, ""):
        return str(value).strip()
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return str(default).strip()


def secret_dict(name):
    try:
        import streamlit as st

        if name in st.secrets:
            return dict(st.secrets[name])
    except Exception:
        pass
    return None


SERPER_API_KEY=setting('SERPER_API_KEY')
SCRAPEDO_TOKEN=setting('SCRAPEDO_TOKEN')
GOOGLE_SHEET_URL=setting('GOOGLE_SHEET_URL',DEFAULT_SHEET_URL)
GOOGLE_SERVICE_ACCOUNT_JSON=setting('GOOGLE_SERVICE_ACCOUNT_JSON','credentials/service_account.json')
GOOGLE_SERVICE_ACCOUNT_INFO=secret_dict('GOOGLE_SERVICE_ACCOUNT_INFO')
GOOGLE_OAUTH_CLIENT_ID=setting('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_OAUTH_CLIENT_SECRET=setting('GOOGLE_OAUTH_CLIENT_SECRET')
GOOGLE_OAUTH_TOKEN_JSON=setting('GOOGLE_OAUTH_TOKEN_JSON','credentials/oauth_token.json')
GOOGLE_OAUTH_TOKEN_INFO=secret_dict('GOOGLE_OAUTH_TOKEN_INFO')
GOOGLE_OAUTH_REDIRECT_PORT=int(setting('GOOGLE_OAUTH_REDIRECT_PORT','8502') or '8502')
DATA_DIR=ROOT/'data'; EXPORT_DIR=ROOT/'exports'; DB_PATH=DATA_DIR/'listingsfinder.db'
for p in (DATA_DIR,EXPORT_DIR,ROOT/'credentials'): p.mkdir(exist_ok=True)
