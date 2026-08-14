#!/usr/bin/env python3
import os
import json
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

COMPANIES = [
    "Google", "Amazon", "Apple", "Meta", "Netflix",
    "Microsoft", "IBM", "Salesforce", "Oracle", "SAP", "Cisco",
    "Adobe", "Intel", "Dell", "HP",
    "Deloitte", "PwC", "EY", "KPMG",
    "Accenture", "McKinsey", "JPMorgan", "Goldman Sachs", "Morgan Stanley",
    "Citigroup", "Bank of America", "American Express", "Visa", "Mastercard", "PayPal",
    "Barclays", "Lloyds Banking Group", "HSBC", "Santander", "Nationwide",
    "Vitality", "Aviva", "Prudential",
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

EXCLUDE_TITLE_KEYWORDS = ["engineer", "engineering", "developer", "software development"]

COUNTRY = "gb"
MAX_DAYS_OLD = 1
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "seen_jobs_1.json")

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
    url = "https://api.adzuna.com/v1/api/jobs/" + COUNTRY + "/search/1"
    query_text = company + " " + keyword
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query_text,
        "max_days_old": MAX_DAYS_OLD,
        "results_per_page": 50,
        "content-type": "application/json",
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.RequestException as e:
        print("  [warn] failed for " + company + "/" + keyword + ": " + str(e))
        return []


def company_matches(ad, company):
    name = (ad.get("company", {}) or {}).get("display_name", "") or ""
    return company.lower() in name.lower()


def format_email(new_ads):
    body = MIMEMultipart("alternative")
    body["Subject"] = "New job posting(s) - Batch 1 (" + str(len(new_ads)) + ")"
    body["From"] = GMAIL_ADDRESS
    body["To"] = TO_EMAIL

    lines = []
    for ad in new_ads:
        title = ad.get("title", "Unknown title")
        company = (ad.get("company", {}) or {}).get("display_name", "Unknown company")
        location = (ad.get("location", {}) or {}).get("display_name", "")
        url = ad.get("redirect_url", "")
        created = ad.get("created", "")
        line = "<p><b>" + str(title) + "</b> - " + str(company) + " (" + str(location) + ")<br>"
        line += "Posted: " + str(created) + "<br>"
        line += "<a href='" + str(url) + "'>" + str(url) + "</a></p><hr>"
        lines.append(line)

    html = "<html><body>" + "".join(lines) + "</body></html>"
    body.attach(MIMEText(html, "html"))
    return body


def send_email(new_ads):
    msg = format_email(new_ads)
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    server.sendmail(GMAIL_ADDRESS, [TO_EMAIL], msg.as_string())
    server.quit()


def main():
    seen = load_seen()
    new_ads = []
    new_ids = set()

    total = len(COMPANIES)
    index = 0
    for company in COMPANIES:
        index = index + 1
        print("[" + str(index) + "/" + str(total) + "] " + company)
        for keyword in KEYWORDS:
            ads = search_adzuna(company, keyword)
            for ad in ads:
                if not company_matches(ad, company):
                    continue
                title_lower = (ad.get("title") or "").lower()
                excluded = False
                for bad in EXCLUDE_TITLE_KEYWORDS:
                    if bad in title_lower:
                        excluded = True
                if excluded:
                    continue
                ad_id = str(ad.get("id"))
                if ad_id in seen or ad_id in new_ids:
                    continue
                new_ids.add(ad_id)
                new_ads.append(ad)
            time.sleep(0.2)

    print("Found " + str(len(new_ads)) + " new job(s).")

    if len(new_ads) > 0:
        send_email(new_ads)

    all_seen = seen.union(new_ids)
    save_seen(all_seen)


if __name__ == "__main__":
    main()
