# Job Watcher

Checks for new job postings every 10 minutes at a configurable list of
companies (defaults to Google, Amazon, IBM, Microsoft, Apple, Meta, and
~15 other large employers) matching your keywords (Account Manager, Sales,
Marketing, Strategy, Operations, Product Manager), and emails you when it
finds new ones.

**How it works:** it queries the [Adzuna](https://developer.adzuna.com/) job
search API (free tier), which aggregates postings from many company career
sites and job boards. It is not a scraper of each company's own site, so
coverage isn't 100% guaranteed for every company — but it's a solid,
low-maintenance way to watch many employers at once.

## One-time setup (you'll need to do these yourself — 10-15 minutes)

### 1. Get free Adzuna API keys
- Sign up at https://developer.adzuna.com/
- Create an app to get an `App ID` and `App Key`

### 2. Create a Gmail App Password
- Requires 2-factor authentication enabled on your Google account
- Go to https://myaccount.google.com/apppasswords and generate a password
  for "Mail" — this lets the script send email without your real password

### 3. Create a GitHub repo and push these files
- Create a **public** repo (public repos get unlimited free GitHub Actions
  minutes; private repos get 2,000 free minutes/month, which is enough too,
  running every 10 min ≈ 4,300 min/month of *scheduled triggers*, but each
  run only takes ~10-20 seconds of actual runtime)
- Push this folder's contents to it

### 4. Add repository secrets
In your repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add each of these:

| Secret name | Value |
|---|---|
| `ADZUNA_APP_ID` | from step 1 |
| `ADZUNA_APP_KEY` | from step 1 |
| `GMAIL_ADDRESS` | your Gmail address |
| `GMAIL_APP_PASSWORD` | the app password from step 2 |
| `TO_EMAIL` | where you want alerts sent (can be same as GMAIL_ADDRESS) |

### 5. Test it
Go to the **Actions** tab in your repo → "Job Watcher" workflow → **Run
workflow** to trigger it manually and confirm you get an email (or a "no new
jobs" log message) without waiting for the schedule.

## Customizing

Edit `scripts/check_jobs.py`:
- `COMPANIES` — add/remove companies
- `KEYWORDS` — add/remove role keywords
- `COUNTRY` — Adzuna country code (`gb`, `us`, `ca`, `au`, etc.)
- `MAX_DAYS_OLD` — how recent a posting must be to count

## Notes / limitations
- "Several minutes" delivery: GitHub's cron scheduler runs every 10 minutes
  but can occasionally lag a few extra minutes under load — it's not
  instant, but it's close.
- Some big employers (e.g., government-adjacent or highly custom career
  sites) may be under-indexed on Adzuna. If you find specific companies
  aren't showing up, let me know and I can add a second source (e.g., their
  Greenhouse/Lever/Workday feed if they use one).
- The first run may email you a burst of "new" jobs since everything looks
  new to it — after that it only alerts on genuinely new postings.
