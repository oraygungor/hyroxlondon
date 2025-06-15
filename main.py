import asyncio, os, smtplib
from pyppeteer import launch
from email.mime.text import MIMEText
from PIL import Image, ImageChops

URL = "https://gb.hyrox.com/checkout/hyrox-london-excel-season-25-26-rzstou"
LAST_IMG = "last.png"
CURR_IMG = "curr.png"

EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

async def take_screenshot(path):
    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.setViewport({'width': 1280, 'height': 1024})
    await page.goto(URL, {'waitUntil': 'networkidle2'})
    await page.screenshot({'path': path})
    await browser.close()

def send_email():
    msg = MIMEText("HYROX page visually changed.")
    msg["Subject"] = "🔔 HYROX Page Change Detected"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.send_message(msg)

def compare_images(img1_path, img2_path):
    if not os.path.exists(img1_path):
        return True
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)
    diff = ImageChops.difference(img1, img2)
    return diff.getbbox() is not None

async def run():
    await take_screenshot(CURR_IMG)
    if compare_images(LAST_IMG, CURR_IMG):
        send_email()
        os.replace(CURR_IMG, LAST_IMG)
    else:
        os.remove(CURR_IMG)

asyncio.get_event_loop().run_until_complete(run())
