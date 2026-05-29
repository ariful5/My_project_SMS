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

def login(session):
    login_url  = f"{BASE_URL}/login"
    signin_url = f"{BASE_URL}/signin"
    resp = session.get(login_url, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    captcha_answer = solve_captcha(soup)
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "capt":     captcha_answer,
    }
    resp = session.post(signin_url, data=login_data, timeout=15, allow_redirects=True)
    print(f"Login URL: {resp.url}")
    if "login" in resp.url.lower() or "signin" in resp.url.lower():
        print("❌ Login failed!")
        return False
    print("✅ Login OK!")
    return True

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "X-Requested-With": "XMLHttpRequest"
    })

    if not login(session):
        return

    # Step 1: CDR page থেকে AJAX URL খোঁজো
    cdr_url = f"{BASE_URL}/client/SMSCDRStats"
    resp = session.get(cdr_url, timeout=15)
    page_text = resp.text

    # JavaScript থেকে DataTables ajax URL বের করো
    ajax_url = None
    match = re.search(r'ajax["\s:]+["\']([^"\']+)["\']', page_text)
    if match:
        ajax_url = match.group(1)
        if not ajax_url.startswith("http"):
            ajax_url = BASE_URL + "/" + ajax_url.lstrip("/")
        print(f"AJAX URL found: {ajax_url}")

    rows = []

    # Step 2: AJAX দিয়ে data আনার চেষ্টা
    if ajax_url:
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        params = {
            "draw": 1,
            "start": 0,
            "length": 100,
            "date_from": f"{today} 00:00:00",
            "date_to":   f"{today} 23:59:59",
        }
        session.headers.update({"X-Requested-With": "XMLHttpRequest"})
        r = session.get(ajax_url, params=params, timeout=15)
        print(f"AJAX status: {r.status_code}")
        try:
            data = r.json()
            print(f"AJAX data keys: {list(data.keys())}")
            # DataTables format: {"data": [[col1, col2, ...]]}
            if "data" in data:
                rows = data["data"]
                print(f"Rows from AJAX: {len(rows)}")
            elif "aaData" in data:
                rows = data["aaData"]
                print(f"Rows from AJAX (aaData): {len(rows)}")
        except Exception as e:
            print(f"AJAX JSON parse error: {e}")
            print(f"AJAX response: {r.text[:500]}")

    # Step 3: AJAX কাজ না করলে common endpoint গুলো try করো
    if not rows:
        print("Trying common AJAX endpoints...")
        endpoints = [
            "/client/getSMSCDR",
            "/client/sms-cdr-data",
            "/client/SMSCDRData",
            "/client/cdr-data",
            "/client/getCDRStats",
        ]
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        params = {
            "draw": 1, "start": 0, "length": 100,
            "date_from": f"{today} 00:00:00",
            "date_to":   f"{today} 23:59:59",
        }
        for ep in endpoints:
            try:
                r = session.get(f"{BASE_URL}{ep}", params=params, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if "data" in data or "aaData" in data:
                        rows = data.get("data", data.get("aaData", []))
                        print(f"✅ Found data at: {ep} ({len(rows)} rows)")
                        break
            except:
                pass

    if not rows:
        print("❌ No data found. Printing page JS for debug:")
        # JS snippet দেখাও
        for line in page_text.split("\n"):
            if "ajax" in line.lower() or "datatable" in line.lower():
                print(f"  JS: {line.strip()[:150]}")
        return

    if rows:
        print(f"Sample row: {rows[0]}")

    # Step 4: New messages only
    seen = load_seen()
    new_rows = []
    for row in rows:
        if isinstance(row, list):
            row_id = "|".join(str(c) for c in row[:5])
        elif isinstance(row, dict):
            row_id = str(row)
            row = list(row.values())
        else:
            continue
        if row_id not in seen:
            new_rows.append((row_id, row))

    print(f"New messages: {len(new_rows)}")

    # Step 5: Telegram
    for row_id, row in new_rows:
        send_telegram(build_message(row))
        seen.add(row_id)

    save_seen(seen)
    print("✅ Done!")

if __name__ == "__main__":
    main()
    
