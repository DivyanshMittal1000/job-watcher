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
# CONFIG
# ---------------------------------------------------------------------------

COMPANIES = [
    "Google", "Amazon", "Apple", "Meta", "Netflix",
    "Microsoft", "IBM", "Salesforce", "Oracle", "SAP", "Cisco",
    "Adobe", "Intel", "Dell", "HP",
    "Deloitte", "PwC", "EY", "KPMG",
    "Accenture", "McKinsey", "JPMorgan", "Goldman Sachs", "Morgan Stanley",
    "Citigroup", "Bank of America", "American Express", "Visa", "Mastercard", "PayPal",
    "Barclays", "Lloyds Banking Group", "HSBC", "Santander", "Nationwide",
    "Vitality", "Aviva", "Prudential", "Legal & General",
    "Procter & Gamble", "Unilever", "PepsiCo", "Coca-Cola", "Walmart",
    "Costco", "Target", "Home Depot", "Johnson & Johnson", "Nike", "Disney",
    "Starbucks", "McDonald's", "Tesco", "Sainsbury's", "Bolt",
    "AT&T", "Verizon", "Ford", "General Motors", "Boeing",
    "ExxonMobil", "Chevron", "UnitedHealth Group", "CVS Health",
    "BP", "Shell", "Vodafone", "BT Group", "GSK", "AstraZeneca",
    "Rolls-Royce", "BAE Systems", "Diageo", "Uber", "Airbnb",
]

KEYWORDS = [
    "Account Manager", "Graduate Account Manager", "Entry Level Account Manager",
    "Sales", "Graduate Sales", "Entry Level Sales",
    "Marketing", "Graduate Marketing",
    "Strategy", "Graduate Strategy",
    "Operations", "Graduate Operations",
    "Product Manager", "Associate Product Manager",
]

EXCLUDE_TITLE_KEYWORDS = ["engineer", "engineering", "developer", "software development"]

COUNTRY = "gb"
MAX_DAYS_OLD = 7
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "seen_jobs.json")

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
        print(f"  [warn] Adzuna request failed for {company}/{keyword}: {e}", flush=True)
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
    total_combos = len(COMPANIES) * len(KEYWORDS)
    print(f"Starting run: {len(COMPANIES)} companies x {len(KEYWORDS)} keywords = {total_combos} combinations", flush=True)

    seen = load_seen()
    print(f"Loaded {len(seen)} previously-seen job IDs", flush=True)

    new_ads = []
    new_ids = set()

    for i, company in enumerate(COMPANIES, 1):
        print(f"
