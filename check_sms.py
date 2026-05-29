import requests
import json
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL     = os.environ["LAMIX_URL"]
USERNAME     = os.environ["LAMIX_USERNAME"]
PASSWORD     = os.environ["LAMIX_PASSWORD"]
TG_TOKEN     = os.environ["TELEGRAM_TOKEN"]
TG_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE    = "seen_ids.json"
DEVELOPER    = "https://t.me/Napa_Ex"

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(ids), f)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "👨‍💻 Developer", "url": DEVELOPER}
            ]]
        }
    }
    r = requests.post(url, json=payload, timeout=10)
    print("Telegram:", r.status_code)

def solve_captcha(soup):
    full_text = soup.get_text(" ", strip=True)
    match = re.search(r'(\d+)\s*\+\s*(\d+)', full_text)
    if match:
        ans = int(match.group(1)) + int(match.group(2))
        print(f"Captcha: {match.group(1)} + {match.group(2)} = {ans}")
        return str(ans)
    match = re.search(r'(\d+)\s*-\s*(\d+)', full_text)
    if match:
        ans = int(match.group(1)) - int(match.group(2))
        print(f"Captcha: {match.group(1)} - {match.group(2)} = {ans}")
        return str(ans)
    print("Captcha not found!")
    return "0"

def format_time(date_str):
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%I:%M %p | %d.%m.%y")
    except:
        return date_str

def build_message(row):
    date_str = row[0] if len(row) > 0 else "N/A"
    range_   = row[1] if len(row) > 1 else "N/A"
    number   = row[2] if len(row) > 2 else "N/A"
    cli      = row[3] if len(row) > 3 else "N/A"
    sms_text = row[4] if len(row) > 4 else "N/A"
    time_fmt = format_time(date_str)
    return (
        f"📱💥 <b>NEW SMS ALERT</b> 💥📱\n\n"
        f"📱 SMS Received\n"
        f"📍 Range » {range_}\n"
        f"🔖 CLI » {cli}\n"
        f"📞 Number » {number}\n\n"
        f"💬 {sms_text}\n\n"
        f"⏰ {time_fmt}"
    )

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })

    # Step 1: Login page
    login_url  = f"{BASE_URL}/login"
    signin_url = f"{BASE_URL}/signin"   # ✅ form action = signin

    resp = session.get(login_url, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    captcha_answer = solve_captcha(soup)

    # Step 2: POST to signin ✅
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "capt":     captcha_answer,   # ✅ field name = capt
    }

    resp = session.post(signin_url, data=login_data, timeout=15, allow_redirects=True)
    print(f"Login URL: {resp.url}")

    if "login" in resp.url.lower() or "signin" in resp.url.lower():
        print("❌ Login failed!")
        return

    print("✅ Login OK!")

    # Step 3: SMS CDR Stats
    cdr_url = f"{BASE_URL}/client/SMSCDRStats"
    resp = session.get(cdr_url, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Step 4: Parse table
    table = soup.find("table")
    if not table:
        print("❌ Table not found")
        return

    tbody = table.find("tbody")
    if not tbody:
        print("❌ No tbody")
        return

    rows = []
    for tr in tbody.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            rows.append(cells)

    print(f"Total rows: {len(rows)}")
    if not rows:
        print("No SMS.")
        return

    # Step 5: New messages only
    seen = load_seen()
    new_rows = []
    for row in rows:
        row_id = "|".join(row[:5])
        if row_id not in seen:
            new_rows.append((row_id, row))

    print(f"New: {len(new_rows)}")

    # Step 6: Telegram alert
    for row_id, row in new_rows:
        send_telegram(build_message(row))
        seen.add(row_id)

    save_seen(seen)
    print("✅ Done!")

if __name__ == "__main__":
    main()
    
