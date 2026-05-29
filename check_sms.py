import requests
import json
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime, date

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
            "inline_keyboard": [[{"text": "👨‍💻 Developer", "url": DEVELOPER}]]
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
    return "0"

def format_time(date_str):
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%I:%M %p | %d.%m.%y")
    except:
        return date_str

def build_message(row):
    date_str = str(row[0]) if len(row) > 0 else "N/A"
    range_   = str(row[1]) if len(row) > 1 else "N/A"
    number   = str(row[2]) if len(row) > 2 else "N/A"
    cli      = str(row[3]) if len(row) > 3 else "N/A"
    sms_text = str(row[4]) if len(row) > 4 else "N/A"
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    # ==================== LOGIN ====================
    login_url  = f"{BASE_URL}/login"
    signin_url = f"{BASE_URL}/signin"

    resp = session.get(login_url, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    captcha_answer = solve_captcha(soup)

    session.headers.update({"Referer": login_url})
    resp = session.post(signin_url, data={
        "username": USERNAME,
        "password": PASSWORD,
        "capt": captcha_answer,
    }, timeout=15, allow_redirects=True)

    print(f"Login URL: {resp.url}")
    if "login" in resp.url.lower() or "signin" in resp.url.lower():
        print("❌ Login failed!")
        return
    print("✅ Login OK!")

    # ==================== SCRAPE DASHBOARD HTML ====================
    dashboard_url = f"{BASE_URL}/client/SMSDashboard"
    print(f"📄 Fetching dashboard: {dashboard_url}")

    resp = session.get(dashboard_url, timeout=20)
    print(f"Dashboard status: {resp.status_code}")

    if resp.status_code != 200:
        print("❌ Failed to load dashboard")
        print(resp.text[:500])
        return

    soup = BeautifulSoup(resp.text, "html.parser")

    # Debug: পেজ টাইটেল ও কয়টা টেবিল আছে
    print(f"Page Title: {soup.title.string if soup.title else 'No title'}")
    tables = soup.find_all("table")
    print(f"Total tables found: {len(tables)}")

    # SMS টেবিল খুঁজে বের করা (সবচেয়ে বড় টেবিল বা DataTable)
    rows = []
    for table in tables:
        tbody = table.find("tbody")
        if tbody:
            trs = tbody.find_all("tr")
            if len(trs) > 3:   # অনেকগুলো রো থাকলে এটাই SMS টেবিল
                print(f"✅ Found promising table with {len(trs)} rows")
                for tr in trs:
                    tds = tr.find_all("td")
                    if len(tds) >= 5:
                        row_data = [td.get_text(strip=True) for td in tds]
                        rows.append(row_data)
                break  # প্রথম বড় টেবিল পেলেই নেব

    print(f"Total SMS rows extracted: {len(rows)}")
    if rows:
        print(f"Sample row: {rows[0]}")

    if not rows:
        print("❌ No SMS rows found in HTML. Need more debug.")
        print("First 800 chars of dashboard:", resp.text[:800])
        return

    # ==================== NEW SMS ONLY ====================
    seen = load_seen()
    new_rows = []
    for row in rows:
        row_id = "|".join(str(c) for c in row[:5])
        if row_id not in seen:
            new_rows.append((row_id, row))

    print(f"New messages: {len(new_rows)}")

    for row_id, row in new_rows:
        send_telegram(build_message(row))
        seen.add(row_id)

    save_seen(seen)
    print("✅ Done!")

if __name__ == "__main__":
    main()
