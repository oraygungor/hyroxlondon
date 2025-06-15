import os, asyncio, smtplib, requests
from email.mime.text import MIMEText
from datetime import datetime as dt
from pyppeteer import launch

# ── CONFIG ───────────────────────────────────────────
URL = "https://gb.hyrox.com/checkout/hyrox-london-excel-season-25-26-rzstou"

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
EMAIL_TO   = os.environ["EMAIL_TO"]

GIST_ID  = os.environ["GIST_ID"]      # the hex id from your private gist URL
GH_TOKEN = os.environ["GH_TOKEN"]     # PAT with only “gist” scope
HEADERS  = {"Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github+json"}
# ─────────────────────────────────────────────────────

def log(msg): print(f"[{dt.utcnow():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)

# ---------- GitHub-Gist helpers ----------------------
def load_baseline() -> list[str] | None:
    res = requests.get(f"https://api.github.com/gists/{GIST_ID}",
                       headers=HEADERS, timeout=15)
    res.raise_for_status()
    file_content = next(iter(res.json()["files"].values()))["content"]
    lines = [ln.strip() for ln in file_content.splitlines() if ln.strip()]
    return lines or None

def save_baseline(lines: list[str]) -> None:
    payload = {
        "files": {"hyrox-baseline.txt": {"content": "\n".join(lines) + "\n"}}
    }
    requests.patch(f"https://api.github.com/gists/{GIST_ID}",
                   headers=HEADERS, json=payload, timeout=15).raise_for_status()
# -----------------------------------------------------

async def fetch_visible_text() -> list[str]:
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.goto(URL, {"waitUntil": "networkidle2"})
    raw = await page.evaluate("document.body.innerText")
    await browser.close()
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]

def send_email(added: list[str]) -> None:
    body = "New text detected on HYROX page:\n\n" + "\n".join(added)
    msg = MIMEText(body)
    msg["Subject"] = "🔔 HYROX page: new text added"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.send_message(msg)

async def main():
    log("===== Job start =====")
    new_lines = await fetch_visible_text()
    log(f"Fetched {len(new_lines)} lines")

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
