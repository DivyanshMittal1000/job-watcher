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
    # FAANG / MAANG
    "Google",
    "Amazon",
    "Apple",
    "Meta",
    "Netflix",
    # Big Tech / enterprise software
    "Microsoft",
    "IBM",
    "Salesforce",
    "Oracle",
    "SAP",
    "Cisco",
    "Adobe",
    "Intel",
    "Dell",
    "HP",
    # Big 4
    "Deloitte",
    "PwC",
    "EY",
    "KPMG",
    # Consulting / Global Finance
    "Accenture",
    "McKinsey",
    "JPMorgan",
    "Goldman Sachs",
    "Morgan Stanley",
    "Citigroup",
    "Bank of America",
    "American Express",
    "Visa",
    "Mastercard",
    "PayPal",
    # UK Banks / Insurance / Financial Services
    "Barclays",
    "Lloyds Banking Group",
    "HSBC",
    "Santander",
    "Nationwide",
    "Vitality",
    "Aviva",
    "Prudential",
    "Legal & General",
    # Consumer / Retail / Fortune 500
    "Procter & Gamble",
    "Unilever",
    "PepsiCo",
    "Coca-Cola",
    "Walmart",
    "Costco",
    "Target",
    "Home Depot",
    "Johnson & Johnson",
    "Nike",
    "Disney",
    "Starbucks",
    "McDonald's",
    "Tesco",
    "Sainsbury's",
    "Bolt",
    # Telecom / Auto / Energy / Industrial / Pharma
    "AT&T",
    "Verizon",
    "Ford",
    "General Motors",
    "Boeing",
    "ExxonMobil",
    "Chevron",
    "UnitedHealth Group",
    "CVS Health",
    "BP",
    "Shell",
    "Vodafone",
    "BT Group",
    "GSK",
    "AstraZeneca",
    "Rolls-Royce",
    "BAE Systems",
    "Diageo",
    # Other big tech / travel
    "Uber",
    "Airbnb",
]

KEYWORDS = [
    "Account Manager",
    "Graduate Account Manager",
    "Entry Level Account Manager",
    "Sales",
    "Graduate Sales",
    "Entry Level Sales",
    "Marketing",
    "Graduate Marketing",
    "Strategy",
    "Graduate Strategy",
    "Operations",
    "Graduate Operations",
    "Product Manager",
    "Associate Product Manager",
]

# Titles containing these words get filtered out even if they match a keyword/company
EXCLUDE_TITLE_KEYWORDS = [
    "engineer",
    "engineering",
    "developer",
    "software development",
]

# Adzuna country code — "gb" for UK, "us" for US, etc.
COUNTRY = "gb"

# How many days back to consider a job "new"
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
