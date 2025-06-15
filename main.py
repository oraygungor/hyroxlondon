# text_monitor.py
import os, asyncio, smtplib, difflib
from pathlib import Path
from datetime import datetime as dt
from email.mime.text import MIMEText

from pyppeteer import launch

# ── CONFIG ───────────────────────────────────────────
URL        = "https://gb.hyrox.com/checkout/hyrox-london-excel-season-25-26-rzstou"
BASE_TXT   = Path("last.txt")

EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO   = os.getenv("EMAIL_TO")
# ─────────────────────────────────────────────────────

def log(msg): print(f"[{dt.utcnow():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)

async def fetch_visible_text() -> list[str]:
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.goto(URL, {"waitUntil": "networkidle2"})
    raw = await page.evaluate("document.body.innerText")
    await browser.close()
    # normalise: split, strip, drop empties
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]

def send_email(added_lines: list[str]) -> None:
    body = "New text detected on HYROX page:\n\n" + "\n".join(added_lines)
    msg = MIMEText(body)
    msg["Subject"] = "🔔 HYROX page: new text added"
    msg["From"] = EMAIL_FROM
    msg["To"]   = EMAIL_TO
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.send_message(msg)

async def main():
    log("===== Job start =====")
    new_lines = await fetch_visible_text()
    log(f"Fetched {len(new_lines)} lines of text")

    if not BASE_TXT.exists():
        BASE_TXT.write_text("\n".join(new_lines), encoding="utf-8")
        log("Baseline created (first run) – no alert")
        return

    old_lines = BASE_TXT.read_text(encoding="utf-8").splitlines()
    added = [ln for ln in new_lines if ln not in old_lines]

    if added:
        log(f"{len(added)} new line(s) → sending e-mail")
        send_email(added)
        BASE_TXT.write_text("\n".join(new_lines), encoding="utf-8")
    else:
        log("✅ No new text")
    log("===== Job finished =====")

if __name__ == "__main__":
    asyncio.run(main())
