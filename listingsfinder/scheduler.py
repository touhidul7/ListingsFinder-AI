from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import smtplib
from zoneinfo import ZoneInfo

import requests

from .config import RESEND_API_KEY, RESEND_FROM_EMAIL, SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from .pipeline import run_search
from .sheets import _sheet

EASTERN = ZoneInfo("America/New_York")
FREQUENCIES = {"one-time", "daily", "weekly", "monthly"}


def _parse_dt(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt).replace(tzinfo=EASTERN)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(EASTERN) if parsed.tzinfo else parsed.replace(tzinfo=EASTERN)
    except ValueError:
        return None


def _next_run(now, frequency):
    base = now.replace(hour=5, minute=0, second=0, microsecond=0)
    if frequency == "daily":
        return base + (timedelta(days=1) if now >= base else timedelta())
    if frequency == "weekly":
        return base + timedelta(days=7)
    if frequency == "monthly":
        month = base.month + 1
        year = base.year + (1 if month == 13 else 0)
        month = 1 if month == 13 else month
        return base.replace(year=year, month=month)
    return ""


def _send_email(to_email, subject, body):
    if RESEND_API_KEY:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={"from": RESEND_FROM_EMAIL, "to": [to_email], "subject": subject, "text": body},
            timeout=30,
        )
        response.raise_for_status()
        return True, "Email sent with Resend"
    if not to_email or not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        return False, "Email provider not configured"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = to_email
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    return True, "Email sent"


def email_status():
    if RESEND_API_KEY:
        return True, "Resend configured"
    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        return True, "SMTP configured"
    return False, "Email provider not configured"


def read_mandate_rows():
    sh, err = _sheet()
    if err:
        return [], err
    try:
        return sh.worksheet("Mandates").get_all_records(), ""
    except Exception as exc:
        return [], str(exc)


def due_mandates(rows, now=None):
    now = now or datetime.now(EASTERN)
    due = []
    for index, row in enumerate(rows, start=2):
        frequency = str(row.get("Frequency", "One-time") or "One-time").strip().lower()
        if frequency not in FREQUENCIES or frequency == "one-time":
            continue
        next_run = _parse_dt(row.get("Next Run"))
        last_run = _parse_dt(row.get("Last Run"))
        if next_run and next_run > now:
            continue
        if not next_run and last_run:
            next_run = _next_run(last_run, frequency)
            if next_run and next_run > now:
                continue
        due.append((index, row, frequency))
    return due


def run_due_mandates():
    sh, err = _sheet()
    if err:
        return [{"ok": False, "message": err}]
    ws = sh.worksheet("Mandates")
    rows = ws.get_all_records()
    headers = ws.row_values(1)
    now = datetime.now(EASTERN)
    results = []

    def col(name):
        return headers.index(name) + 1 if name in headers else None

    for row_index, row, frequency in due_mandates(rows, now):
        mandate = row.get("Original Query") or row.get("Search Query")
        if not mandate:
            continue
        mandate_id = row.get("Mandate ID") or ""
        criteria, queries, listings, duplicates, potential, run, sheet_results, csv_paths = run_search(
            mandate,
            write_sheets=True,
            mandate_id=mandate_id,
            log_mandate=False,
            frequency=frequency.title(),
        )
        last_run_value = now.isoformat(timespec="seconds")
        next_run_value = _next_run(now, frequency)
        if col("Last Run"):
            ws.update_cell(row_index, col("Last Run"), last_run_value)
        if col("Next Run"):
            ws.update_cell(row_index, col("Next Run"), next_run_value.isoformat(timespec="seconds") if next_run_value else "")
        if col("Status"):
            ws.update_cell(row_index, col("Status"), "Scheduled")
        email_status = None
        notify_email = row.get("Notify Email")
        if notify_email and listings:
            body = "\n".join([f"{item.listing_title} - {item.source_url}" for item in listings[:25]])
            email_status = _send_email(notify_email, f"ListingsFinder: {len(listings)} listings found", body)
        elif not notify_email:
            email_status = (False, "No Notify Email set")
        elif not listings:
            email_status = (False, "No listings found, email skipped")
        results.append(
            {
                "ok": True,
                "mandate_id": mandate_id,
                "query": mandate,
                "listings": len(listings),
                "duplicates": len(duplicates),
                "email": email_status,
            }
        )
    return results


if __name__ == "__main__":
    results = run_due_mandates()
    if not results:
        print("No due mandates found.")
    for result in results:
        print(result)
