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

# ── Country Price List (USD) ─────────────────────────────────────────────────
COUNTRY_PRICES = { ... }  # আপনার আগের প্রাইস লিস্ট অপরিবর্তিত থাকবে

def get_price_from_range(range_str):
    """Range string থেকে country match করে price বের করো"""
    r = range_str.lower()
    for country, price in sorted(COUNTRY_PRICES.items(), key=lambda x: -len(x[0])):
        if country in r:
            return price
    return 0.0

def calc_daily_income(rows):
    total = 0.0
    for row in rows:
        if isinstance(row, dict):
            row = list(row.values())
        number = str(row[2]).strip() if len(row) > 2 else ""
        range_ = str(row[1]).strip() if len(row) > 1 else ""
        if number in ("0", "", "N/A"):
            continue
        total += get_price_from_range(range_)
    return round(total, 4)

# ── Helpers ──────────────────────────────────────────────────────────────────
def get_session_date():
    bd_now = datetime.utcnow() + timedelta(hours=6)
    return (bd_now - timedelta(hours=6)).strftime("%Y-%m-%d")

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            data = json.load(f)
            if isinstance(data, list):
                print("📅 পুরনো format! seen_ids রিসেট হলো।")
                return set()
            saved_date = data.get("date", "")
            if saved_date == get_session_date():
                return set(data.get("ids", []))
            else:
                print("📅 নতুন দিন! seen_ids রিসেট হলো।")
                return set()
    return set()

def save_seen(ids):
    data = {"date": get_session_date(), "ids": list(ids)}
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f)

def push_seen():
    os.system('git config user.email "action@github.com"')
    os.system('git config user.name "GitHub Action"')
    os.system(f'git add {SEEN_FILE}')
    os.system('git commit -m "chore: update seen_ids" || true')
    os.system('git push --force || true')

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
        bd_time = dt + timedelta(hours=6)
        return bd_time.strftime("%I:%M %p | %d.%m.%y")
    except:
        return date_str

# নতুন ফাংশন: CLI ভিত্তিতে আজকের কাউন্ট
def get_cli_count_today(rows, cli):
    cli = str(cli).strip().upper()
    count = 0
    for row in rows:
        if isinstance(row, dict):
            row = list(row.values())
        row_cli = str(row[3]).strip().upper() if len(row) > 3 else ""
        if row_cli == cli:
            count += 1
    return count

def build_message(row, total_today_number, daily_income, cli_count):
    date_str = str(row[0]) if len(row) > 0 else "N/A"
    range_   = str(row[1]) if len(row) > 1 else "N/A"
    number   = str(row[2]) if len(row) > 2 else "N/A"
    cli      = str(row[3]) if len(row) > 3 else "N/A"
    sms_text = str(row[4]) if len(row) > 4 else "N/A"
    sms_text = sms_text.replace("$", "").strip()

    return (
        f"🔔 নতুন SMS এসেছে!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📞 Number : {number}\n"
        f"📍 Range  : {range_}\n"
        f"🔖 CLI    : {cli}\n"
        f"📊 Today  : {total_today_number} SMS\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💬 {sms_text} [{cli_count}]\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {format_time(date_str)} | 💰 {daily_income:.4f}$"
    )

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    # ... (লগিন এবং AJAX অংশ আগের মতোই থাকবে)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    # Login (আগের কোড অপরিবর্তিত)
    resp = session.get(f"{BASE_URL}/login", timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    captcha = solve_captcha(soup)

    resp = session.post(f"{BASE_URL}/signin", data={
        "username": USERNAME, "password": PASSWORD, "capt": captcha
    }, timeout=15, allow_redirects=True)

    if "login" in resp.url.lower():
        print("❌ Login failed!")
        return
    print("✅ Login OK!")

    # AJAX Request (আগের মতো)
    today = date.today().strftime("%Y-%m-%d")
    ajax_url = f"{BASE_URL}/client/res/data_smscdr.php"

    params = { ... }  # আগের params অপরিবর্তিত

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

    daily_income = calc_daily_income(rows)
    print(f"Today's income so far: ${daily_income:.4f}")

    seen = load_seen()
    new_rows = []

    for row in rows:
        if isinstance(row, dict):
            row = list(row.values())
        if str(row[2]).strip() in ("0", "", "N/A"):
            continue
        row_id = "|".join(str(c) for c in row[:5])
        if row_id not in seen:
            new_rows.append((row_id, row))

    print(f"New messages to notify: {len(new_rows)}")

    for row_id, row in new_rows:
        number = str(row[2]).strip()
        cli = str(row[3]).strip()

        total_today_number = sum(1 for r in rows if str((list(r.values()) if isinstance(r, dict) else r)[2]).strip() == number)
        cli_count_today = get_cli_count_today(rows, cli)

        send_telegram(build_message(row, total_today_number, daily_income, cli_count_today))
        seen.add(row_id)

    save_seen(seen)
    push_seen()
    print("✅ Done!")

if __name__ == "__main__":
    main()
