import requests
import json
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime

# ── Config from GitHub Secrets ───────────────────────────────────────────────
BASE_URL     = os.environ["LAMIX_URL"]       # http://51.210.208.26/ints
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
                {
                    "text": "👨‍💻 Developer",
                    "url": DEVELOPER
                }
            ]]
        }
    }
    r = requests.post(url, json=payload, timeout=10)
    print("Telegram:", r.status_code)

def solve_captcha(html_text):
    """Solve simple math captcha like 'What is 6 + 7 = ?'"""
    match = re.search(r'(\d+)\s*\+\s*(\d+)', html_text)
    if match:
        return str(int(match.group(1)) + int(match.group(2)))
    match = re.search(r'(\d+)\s*-\s*(\d+)', html_text)
    if match:
        return str(int(match.group(1)) - int(match.group(2)))
    match = re.search(r'(\d+)\s*\*\s*(\d+)', html_text)
    if match:
        return str(int(match.group(1)) * int(match.group(2)))
    return "0"

def format_time(date_str):
    """2026-05-29 01:22:05  →  01:22 AM | 29.05.26"""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%I:%M %p | %d.%m.%y")
    except:
        return date_str

def build_message(row):
    # row = [date, range, number, cli, sms]
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

    # Step 1: Load login page & solve captcha
    login_url = f"{BASE_URL}/login"
    resp = session.get(login_url, timeout=15)
    captcha_answer = solve_captcha(resp.text)
    print(f"Captcha answer: {captcha_answer}")

    # Get CSRF token if exists
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf = ""
    token_input = soup.find("input", {"name": "_token"})
    if token_input:
        csrf = token_input.get("value", "")

    # Step 2: Login
    login_data = {
        "_token":   csrf,
        "username": USERNAME,
        "password": PASSWORD,
        "captcha":  captcha_answer,
    }
    resp = session.post(login_url, data=login_data, timeout=15, allow_redirects=True)
    print(f"After login URL: {resp.url}")

    if "login" in resp.url:
        print("❌ Login failed!")
        return

    # Step 3: Go to SMS CDR Stats page
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
        print("❌ No tbody found")
        return

    rows = []
    for tr in tbody.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            rows.append(cells)

    print(f"Total rows found: {len(rows)}")

    if not rows:
        print("No SMS records.")
        return

    # Step 5: Find new messages
    seen = load_seen()
    new_rows = []

    for row in rows:
        row_id = "|".join(row[:5])
        if row_id not in seen:
            new_rows.append((row_id, row))

    print(f"New messages: {len(new_rows)}")

    # Step 6: Send Telegram alerts
    for row_id, row in new_rows:
        msg = build_message(row)
        send_telegram(msg)
        seen.add(row_id)

    # Step 7: Save seen IDs
    save_seen(seen)
    print("✅ Done!")

if __name__ == "__main__":
    main()
    
