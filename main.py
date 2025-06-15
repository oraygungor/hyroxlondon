# main.py
import os, asyncio, smtplib
from email.mime.text import MIMEText
from datetime import datetime as dt
from pathlib import Path

from pyppeteer import launch
from PIL import Image, ImageChops

# ── CONFIG ───────────────────────────────────────────
URL        = "https://gb.hyrox.com/checkout/hyrox-london-excel-season-25-26-rzstou"
WIDTH      = 1280
HEIGHT     = 1024
BASE_IMG   = Path("last.png")
CURR_IMG   = Path("curr.png")

EMAIL_FROM = os.getenv("EMAIL_FROM")  # your gmail address
EMAIL_PASS = os.getenv("EMAIL_PASS")  # 16-char Gmail *app* password
EMAIL_TO   = os.getenv("EMAIL_TO")    # where alerts go
# ─────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"[{dt.utcnow():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)

async def screenshot(path: Path):
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.setViewport({'width': WIDTH, 'height': HEIGHT})
    await page.goto(URL, {'waitUntil': 'networkidle2'})
    await page.screenshot({'path': str(path)})
    await browser.close()

def images_differ(a: Path, b: Path) -> bool:
    if not a.exists():
        return True
    diff = ImageChops.difference(Image.open(a), Image.open(b))
    return diff.getbbox() is not None

def send_email():
    msg = MIMEText("HYROX page visually changed.")
    msg["Subject"] = "🔔 HYROX page changed"
    msg["From"] = EMAIL_FROM
    msg["To"]   = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.send_message(msg)

async def main():
    log("===== Job start =====")
    await screenshot(CURR_IMG)
    log("📸 Screenshot taken")

    if images_differ(BASE_IMG, CURR_IMG):
        log("🔍 Change detected – e-mailing")
        send_email()
        CURR_IMG.replace(BASE_IMG)  # overwrite baseline
        log("📬 Email sent")
    else:
        log("✅ No change")
        CURR_IMG.unlink()  # discard identical shot

    log("===== Job finished =====")

if __name__ == "__main__":
    asyncio.run(main())
