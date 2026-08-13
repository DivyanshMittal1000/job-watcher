#!/usr/bin/env python3
"""
Job watcher: checks Adzuna's job API for new postings matching target
companies + keywords, and emails you about any new ones since last run.

Runs on a schedule via GitHub Actions (see .github/workflows/job_watcher.yml).
"""

import os
import json
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------------------------------------------------------------------
# CONFIG — edit these lists to change what you're watching for
# ---------------------------------------------------------------------------

COMPANIES = [
    "Google",
    "Amazon",
    "IBM",
    "Microsoft",
    "Apple",
    "Meta",
    "Salesforce",
    "Oracle",
    "SAP",
    "Cisco",
    "Deloitte",
    "Accenture",
    "McKinsey",
    "JPMorgan",
    "Goldman Sachs",
    "Procter & Gamble",
    "Unilever",
    "PepsiCo",
    "Coca-Cola",
    "Walmart",
]

KEYWORDS = [
    "Graduate Account Manager",
    "Account Manager Graduate Scheme",
    "Graduate Scheme Account Management",
    "Entry Level Account Manager",
    "Account Manager New Graduate",
    "Early Careers Account Manager"
    "Account Manager",
    "Sales",
    "Marketing",
    "Strategy",
    "Operations",
    "Product Manager",
]

# Adzuna country code — "gb" for UK, "us" for US, etc.
COUNTRY = "gb"

# How many days back to consider a job "new" (keep small so we don't re-alert
# on old jobs the first time this runs)
MAX_DAYS_OLD = 3

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "seen_jobs.json")

# ---------------------------------------------------------------------------
# Credentials — pulled from environment variables (set as GitHub secrets)
# ---------------------------------------------------------------------------

ADZUNA_APP_ID = os.environ["ADZUNA_APP_ID"]
ADZUNA_APP_KEY = os.environ["ADZUNA_APP_KEY"]
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
TO_EMAIL = os.environ.get("TO_EMAIL", GMAIL_ADDRESS)


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen_ids):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(seen_ids), f, indent=2)


def search_adzuna(company, keyword):
    """Query Adzuna for jobs matching `company keyword`, return list of ads."""
    url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": f"{company} {keyword}",
        "max_days_old": MAX_DAYS_OLD,
        "results_per_page": 50,
        "content-type": "application/json",
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.RequestException as e:
        print(f"  [warn] Adzuna request failed for {company}/{keyword}: {e}")
        return []


def company_matches(ad, company):
    name = (ad.get("company", {}) or {}).get("display_name", "") or ""
    return company.lower() in name.lower()


def format_email(new_ads):
    body = MIMEMultipart("alternative")
    body["Subject"] = f"🔔 {len(new_ads)} new job posting(s) matching your watch list"
    body["From"] = GMAIL_ADDRESS
    body["To"] = TO_EMAIL

    lines = []
    for ad in new_ads:
        title = ad.get("title", "Unknown title")
        company = (ad.get("company", {}) or {}).get("display_name", "Unknown company")
        location = (ad.get("location", {}) or {}).get("display_name", "")
        url = ad.get("redirect_url", "")
        created = ad.get("created", "")
        lines.append(
            f"<p><b>{title}</b> — {company} ({location})<br>"
            f"Posted: {created}<br>"
            f"<a href='{url}'>{url}</a></p><hr>"
        )
    html = "<html><body>" + "".join(lines) + "</body></html>"
    body.attach(MIMEText(html, "html"))
    return body


def send_email(new_ads):
    msg = format_email(new_ads)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [TO_EMAIL], msg.as_string())


def main():
    seen = load_seen()
    new_ads = []
    new_ids = set()

    for company in COMPANIES:
        for keyword in KEYWORDS:
            ads = search_adzuna(company, keyword)
            for ad in ads:
                if not company_matches(ad, company):
                    continue
                ad_id = str(ad.get("id"))
                if ad_id in seen or ad_id in new_ids:
                    continue
                new_ids.add(ad_id)
                new_ads.append(ad)
            time.sleep(0.3)  # be polite to the API

    if new_ads:
        print(f"Found {len(new_ads)} new job(s). Sending email...")
        send_email(new_ads)
    else:
        print("No new jobs found this run.")

    save_seen(seen | new_ids)


if __name__ == "__main__":
    main()
