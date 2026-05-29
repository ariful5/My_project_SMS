import requests
import json
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta

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

def push_seen():
    os.system('git config user.email "action@github.com"')
    os.system('git config user.name "GitHub Action"')
    os.system(f'git add {SEEN_FILE}')
    os.system('git commit -m "chore: update seen_ids" || true')
    os.system('git push || true')

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [[{"text": "👨‍💻 Developer", "url": DEVELOPER}]]}
    }
    requests.post(url, json=payload, timeout=10)

def solve_captcha(soup):
    text = soup.get_text(" ", strip=True)
    match = re.search(r'(\d+)\s*([+\-])\s*(\d+)', text)
    if match:
        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
        ans = a + b if op == '+' else a - b
        print(f"Captcha: {a} {op} {b} = {ans}")
        return str(ans)
    return "0"

def format_time(date_str):
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
        # Bangladesh Time = UTC+6
        bd_time = dt + timedelta(hours=6)
        return bd_time.strftime("%I:%M %p | %d.%m.%y")
    except:
        return date_str

def build_message(row):
    date_str = str(row[0]) if len(row) > 0 else "N/A"
    range_   = str(row[1]) if len(row) > 1 else "N/A"
    number   = str(row[2]) if len(row) > 2 else "N/A"
    cli      = str(row[3]) if len(row) > 3 else "N/A"
    sms_text = str(row[4]) if len(row) > 4 else "N/A"  # ← শুধু row[4]
    sms_text = sms_text.replace("$", "").strip()

    return (
        f"🔔 নতুন SMS এসেছে!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📍 Range  : {range_}\n"
        f"📞 Number : {number}\n"
        f"🔖 CLI    : {cli}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💬 {sms_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {format_time(date_str)}"
    )

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    # Login
    resp = session.get(f"{BASE_URL}/login", timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    captcha = solve_captcha(soup)

    resp = session.post(f"{BASE_URL}/signin", data={
        "username": USERNAME, "password": PASSWORD, "capt": captcha
    }, timeout=15, allow_redirects=True)

    print(f"Login URL: {resp.url}")
    if "login" in resp.url.lower():
        print("❌ Login failed!")
        return
    print("✅ Login OK!")

    # AJAX Request
    today = date.today().strftime("%Y-%m-%d")
    ajax_url = f"{BASE_URL}/client/res/data_smscdr.php"

    params = {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
        "frange": "", "fnum": "", "fcli": "",
        "fgdate": "", "fgmonth": "", "fgrange": "", "fgnumber": "", "fgcli": "",
        "fg": "0", "sEcho": "1", "iColumns": "7", "sColumns": ",,,,,,",
        "iDisplayStart": "0",
        "iDisplayLength": "100",  # ← 25 থেকে 100 করুন
        "mDataProp_0": "0", "mDataProp_1": "1", "mDataProp_2": "2",
        "mDataProp_3": "3", "mDataProp_4": "4", "mDataProp_5": "5", "mDataProp_6": "6",
        "sSearch": "", "bRegex": "false", "iSortCol_0": "0", "sSortDir_0": "desc",
        "iSortingCols": "1", "_": str(int(datetime.now().timestamp() * 1000))
    }

    session.headers.update({
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/client/SMSCDRStats",
        "Origin": BASE_URL,
    })

    r = session.get(ajax_url, params=params, timeout=20)

    if r.status_code == 200:
        data = r.json()
        rows = data.get("aaData") or data.get("data") or []
        print(f"Total rows received: {len(rows)}")
    else:
        print(f"AJAX Error: {r.status_code}")
        return

    # নতুন মেসেজ চেক করো
    seen = load_seen()
    new_rows = []

    for row in rows:
        if isinstance(row, dict):
            row = list(row.values())
        
        # ফাঁকা/invalid row বাদ দাও
        if str(row[2]).strip() in ("0", "", "N/A"):
            continue
        
        row_id = "|".join(str(c) for c in row[:5])
        if row_id not in seen:
            new_rows.append((row_id, row))

    print(f"New messages to notify: {len(new_rows)}")

    for row_id, row in new_rows:
        send_telegram(build_message(row))
        seen.add(row_id)

    # সেভ করো এবং রিপোতে push করো
    save_seen(seen)
    push_seen()
    print("✅ Done!")

if __name__ == "__main__":
    main()
