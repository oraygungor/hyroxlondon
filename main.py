```python
# main.py  – text-only monitor that looks **inside the HYROX checkout iframe**
# Baseline is stored in a private GitHub Gist.

import os, asyncio, smtplib, requests
from email.mime.text import MIMEText
from datetime import datetime as dt
from pyppeteer import launch

# ── ENV / CONFIG ─────────────────────────────────────
URL = "https://gb.hyrox.com/checkout/hyrox-london-excel-season-25-26-rzstou"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EMAIL_TO   = os.environ["EMAIL_TO"]

GIST_ID  = os.environ["GIST_ID"]      # hex id from your secret gist URL
GH_TOKEN = os.environ["GH_TOKEN"]     # PAT (gist scope)
_HEADERS = {"Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github+json"}
# ─────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"[{dt.utcnow():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)

# ---------- GitHub-Gist helpers ----------------------
def load_baseline() -> list[str] | None:
    r = requests.get(f"https://api.github.com/gists/{GIST_ID}",
                     headers=_HEADERS, timeout=15)
    r.raise_for_status()
    content = next(iter(r.json()["files"].values()))["content"]
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    return lines or None

def save_baseline(lines: list[str]) -> None:
    payload = {"files": {"hyrox-baseline.txt": {"content": "\n".join(lines) + "\n"}}}
    requests.patch(f"https://api.github.com/gists/{GIST_ID}",
                   headers=_HEADERS, json=payload, timeout=15).raise_for_status()
# -----------------------------------------------------

async def fetch_ticket_lines() -> list[str]:
    """Return visible text from inside the checkout iframe."""
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.goto(URL, {"waitUntil": "networkidle2"})

    # wait for the checkout iframe to load
    await page.waitForSelector("iframe[src*='secure.checkout']", {"timeout": 15000})
    frame = next(f for f in page.frames if "secure.checkout" in f.url)

    # extract lines of innerText from the iframe document
    raw = await frame.evaluate("document.body.innerText")
    await browser.close()
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]

def send_email(added: list[str]) -> None:
    body = "New text detected on HYROX checkout page:\n\n" + "\n".join(added)
    msg = MIMEText(body)
    msg["Subject"] = "🔔 HYROX page: new text added"
    msg["From"] = EMAIL_FROM
    msg["To"]   = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.send_message(msg)

async def main() -> None:
    log("===== Job start =====")
    new_lines = await fetch_ticket_lines()
    log(f"Fetched {len(new_lines)} lines inside iframe")

    old_lines = load_baseline()
    if old_lines is None:
        save_baseline(new_lines)
        log("Baseline created – no alert")
        return

    added = [ln for ln in new_lines if ln not in old_lines]
    if added:
        log(f"{len(added)} new line(s) → sending email")
        send_email(added)
        save_baseline(new_lines)
    else:
        log("✅ No new text")
    log("===== Job finished =====")

if __name__ == "__main__":
    asyncio.run(main())
```
