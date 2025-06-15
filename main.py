import os, asyncio, smtplib, requests
from email.mime.text import MIMEText
from datetime import datetime as dt
from pyppeteer import launch

URL = "https://gb.hyrox.com/checkout/hyrox-london-excel-season-25-26-rzstou"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EMAIL_TO   = os.environ["EMAIL_TO"]

GIST_ID  = os.environ["GIST_ID"]
GH_TOKEN = os.environ["GH_TOKEN"]
HEADERS  = {
    "Authorization": f"token {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
}

def log(m):  # quick timestamped logger
    print(f"[{dt.utcnow():%H:%M:%S}] {m}", flush=True)

# ---------- GitHub-Gist helpers ----------
def load_baseline() -> set[str]:
    r = requests.get(f"https://api.github.com/gists/{GIST_ID}",
                     headers=HEADERS, timeout=15)
    r.raise_for_status()
    txt = next(iter(r.json()["files"].values()))["content"]
    return set(ln.strip() for ln in txt.splitlines() if ln.strip())

def save_baseline(lines: set[str]):
    payload = {"files": {"hyrox-baseline.txt": {"content": "\n".join(lines) + "\n"}}}
    requests.patch(f"https://api.github.com/gists/{GIST_ID}",
                   headers=HEADERS, json=payload, timeout=15).raise_for_status()
# -----------------------------------------

async def fetch_visible_categories() -> set[str]:
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.goto(URL, {"waitUntil": "networkidle2"})
    await page.waitForSelector("iframe[src*='secure.checkout']", {"timeout": 15000})
    frame = next(f for f in page.frames if "secure.checkout" in f.url)

    cats = await frame.evaluate("""
      [...document.querySelectorAll('[data-ticket-type-name]')]
        .filter(el => el.offsetWidth && el.offsetHeight)
        .map(el => el.getAttribute('data-ticket-type-name').trim())
    """)
    await browser.close()
    return set(cats)

def send_email(new_cats: set[str]):
    body = "New ticket categories detected:\n\n" + "\n".join(sorted(new_cats))
    msg = MIMEText(body)
    msg["Subject"] = "🔔 HYROX – new ticket category added"
    msg["From"], msg["To"] = EMAIL_FROM, EMAIL_TO
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.send_message(msg)

async def main():
    log("Job start")
    current = await fetch_visible_categories()
    log("Now visible: " + (", ".join(sorted(current)) or "[none]"))

    baseline = load_baseline()
    if not baseline:
        save_baseline(current)
        log("Baseline created – no alert")
        return

    added = current - baseline
    if added:
        log("New categories → emailing & updating baseline")
        send_email(added)
        save_baseline(current)
    else:
        log("✅ No new categories")

    log("Job finished")

if __name__ == "__main__":
    asyncio.run(main())
