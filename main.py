# main.py
import os, asyncio, smtplib
from pathlib import Path
from datetime import datetime as dt
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

from pyppeteer import launch
from PIL import Image, ImageChops, ImageDraw

# ── CONFIG ───────────────────────────────────────────
URL        = "https://gb.hyrox.com/checkout/hyrox-london-excel-season-25-26-rzstou"
VIEWPORT   = {'width': 1280, 'height': 1024}

BASE_IMG   = Path("last.png")
CURR_IMG   = Path("curr.png")
DIFF_IMG   = Path("diff.png")

EMAIL_FROM = os.getenv("EMAIL_FROM")  # gmail address
EMAIL_PASS = os.getenv("EMAIL_PASS")  # 16-char Gmail app-password
EMAIL_TO   = os.getenv("EMAIL_TO")    # recipient
# ─────────────────────────────────────────────────────


def log(msg: str) -> None:
    print(f"[{dt.utcnow():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


async def screenshot(path: Path) -> None:
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.setViewport(VIEWPORT)
    await page.goto(URL, {"waitUntil": "networkidle2"})
    await page.screenshot({"path": str(path)})
    await browser.close()


def images_differ(old: Path, new: Path) -> bool:
    """Save a highlighted diff image and return True if any pixel changed."""
    if not old.exists():
        return True

    # raw pixel diff
    diff = ImageChops.difference(Image.open(old), Image.open(new))
    mask = diff.convert("L").point(lambda p: 255 if p > 30 else 0)  # threshold

    if mask.getbbox() is None:          # completely identical
        return False

    # create highlight overlay (red pixels where changed)
    highlight = Image.open(new).convert("RGBA")
    draw = ImageDraw.Draw(highlight, "RGBA")
    for y in range(highlight.height):
        for x in range(highlight.width):
            if mask.getpixel((x, y)):
                draw.point((x, y), fill=(255, 0, 0, 120))  # semi-transparent red
    highlight.save(DIFF_IMG)
    return True


def send_email(with_attachment: bool) -> None:
    if with_attachment and DIFF_IMG.exists():
        msg = MIMEMultipart()
        msg["Subject"] = "🔔 HYROX page changed"
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg.attach(MIMEText("HYROX page visually changed. See diff.png."))

        with open(DIFF_IMG, "rb") as fp:
            img_part = MIMEImage(fp.read(), name="diff.png")
        msg.attach(img_part)
    else:
        msg = MIMEText("HYROX page visually changed.")
        msg["Subject"] = "🔔 HYROX page changed"
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.send_message(msg)


async def main() -> None:
    log("===== Job start =====")
    await screenshot(CURR_IMG)
    log("📸 Screenshot taken")

    if images_differ(BASE_IMG, CURR_IMG):
        log("🔍 Change detected – e-mailing")
        send_email(with_attachment=True)
        CURR_IMG.replace(BASE_IMG)
        log("📬 Email sent")
    else:
        log("✅ No change")
        CURR_IMG.unlink()            # discard identical screenshot

    log("===== Job finished =====")


if __name__ == "__main__":
    asyncio.run(main())
