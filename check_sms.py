import requests
import json
import os
import re
import time
import threading
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta

# ── Global Config ─────────────────────────────────────────────────────────────
BASE_URL         = os.environ["LAMIX_URL"]
TG_TOKEN         = os.environ["TELEGRAM_TOKEN"]
ADMIN_ID         = os.environ["ADMIN_CHAT_ID"]
USERS_FILE       = "users.json"
DEVELOPER        = "https://t.me/Napa_Ex"
RUN_DURATION = 359 * 60
CHECK_INTERVAL   = 1
CURRENT_WORKFLOW = os.environ.get("WORKFLOW_NAME", "")

# ── Language Texts ────────────────────────────────────────────────────────────
TEXTS = {
    "bn": {
        "login_failed": (
            "❌ <b>Login ব্যর্থ হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⚠️ Username অথবা Password ভুল আছে।\n"
            "সঠিক তথ্য দিয়ে আবার চেষ্টা করুন।"
        ),
        "sms_started": (
            "✅ <b>SMS চেকার চালু হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⏱ চলবে: {duration}\n"
            "🔄 চেক হবে: প্রতি ১ সেকেন্ডে"
        ),
        "sms_stopped": (
            "⛔ <b>SMS চেকার বন্ধ হয়ে গেছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⏱ {duration} সময় শেষ হয়ে গেছে।\n"
            "━━━━━━━━━━━━━━━\n"
            "🔄 আবার চালু করতে:\n"
            "👉 /sms_start কমান্ড দিন"
        ),
        "new_sms": "🔔 নতুন SMS এসেছে!",
        "number": "📞 Number",
        "range": "📍 Range",
        "cli": "🔖 CLI",
        "today": "📊 Today",
        "sms_count": "SMS",
        "time_hour": "ঘন্টা",
        "time_min": "মিনিট",
        "time_sec": "সেকেন্ড",
    },
    "en": {
        "login_failed": (
            "❌ <b>Login failed!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⚠️ Username or password is incorrect.\n"
            "Please try again with correct credentials."
        ),
        "sms_started": (
            "✅ <b>SMS checker started!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⏱ Duration: {duration}\n"
            "🔄 Checking every 1 second"
        ),
        "sms_stopped": (
            "⛔ <b>SMS checker stopped!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⏱ {duration} has elapsed.\n"
            "━━━━━━━━━━━━━━━\n"
            "🔄 To start again:\n"
            "👉 Send /sms_start"
        ),
        "new_sms": "🔔 New SMS received!",
        "number": "📞 Number",
        "range": "📍 Range",
        "cli": "🔖 CLI",
        "today": "📊 Today",
        "sms_count": "SMS",
        "time_hour": "hr",
        "time_min": "min",
        "time_sec": "sec",
    }
}

def get_lang(user_data):
    return user_data.get("language") or "bn"

def t(user_data, key, **kwargs):
    lang = get_lang(user_data)
    text = TEXTS.get(lang, TEXTS["bn"]).get(key, TEXTS["bn"].get(key, ""))
    if kwargs:
        text = text.format(**kwargs)
    return text

# ── Country Price List ────────────────────────────────────────────────────────
COUNTRY_PRICES = {
    "afghanistan": 0.0078, "algeria": 0.0108, "angola": 0.009, "argentina": 0.0078,
    "armenia": 0.0078, "karabakh": 0.0078, "azerbaijan": 0.006, "belarus": 0.006,
    "benin": 0.0078, "bhutan": 0.006, "bolivia": 0.006, "bulgaria": 0.006,
    "burkina": 0.006, "cambodia": 0.0138, "cameroon": 0.0078, "comoros": 0.0138,
    "ecuador": 0.006, "egypt": 0.006, "ethiopia": 0.0078, "gabon": 0.0078,
    "georgia": 0.0072, "germany": 0.0078, "guinea": 0.0078, "indonesia": 0.0072,
    "iraq": 0.0078, "ivory coast": 0.006, "ivory": 0.006, "jordan": 0.0078,
    "kazakhstan": 0.0078, "kenya": 0.0078, "kosovo": 0.006, "kuwait": 0.006,
    "kyrgyzstan": 0.0078, "lesotho": 0.0078, "libya": 0.0078, "madagascar": 0.0072,
    "malaysia": 0.0114, "mauritania": 0.0078, "moldova": 0.0072, "mongolia": 0.006,
    "morocco": 0.0078, "mozambique": 0.006, "myanmar": 0.0102, "nepal": 0.006,
    "niger": 0.0078, "nigeria": 0.0078, "oman": 0.0072, "pakistan": 0.0078,
    "palestine": 0.0126, "russia many": 0.006, "russia": 0.0078, "saudi": 0.006,
    "senegal": 0.0078, "slovenia k": 0.006, "slovenia": 0.0072, "sri lanka": 0.0138,
    "sri": 0.0138, "sudan": 0.0072, "sudatel": 0.0072, "syria": 0.0078,
    "tajikistan": 0.006, "tanzania": 0.015, "tunisia": 0.009, "uganda": 0.0072,
    "ukraine": 0.0072, "united arab emirates": 0.006, "uae": 0.006,
    "uzbekistan": 0.0078, "vietnam": 0.0078, "mobifone": 0.0078, "zimbabwe": 0.0078,
}

# ── Seen IDs (per user, separate file) ───────────────────────────────────────
seen_lock = threading.Lock()

def get_session_date():
    bd_now = datetime.utcnow() + timedelta(hours=6)
    return (bd_now - timedelta(hours=6)).strftime("%Y-%m-%d")

def load_seen(seen_file):
    if os.path.exists(seen_file):
        with open(seen_file) as f:
            data = json.load(f)
            if data.get("date") == get_session_date():
                return set(data.get("ids", []))
    return set()

def save_seen(seen_file, seen_ids):
    with seen_lock:
        data = {"date": get_session_date(), "ids": list(seen_ids)}
        with open(seen_file, "w") as f:
            json.dump(data, f)

def push_seen(seen_file):
    os.system('git config user.email "action@github.com"')
    os.system('git config user.name "GitHub Action"')
    os.system('git stash || true')
    os.system('git pull --rebase origin main || true')
    os.system('git stash pop || true')
    os.system(f'git add {seen_file}')
    os.system('git commit -m "chore: update seen_ids" || true')
    os.system('git push origin main || true')

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_price_from_range(range_str):
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

def format_time(date_str):
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
        bd_time = dt + timedelta(hours=6)
        return bd_time.strftime("%I:%M %p | %d.%m.%y")
    except:
        return date_str

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

def seconds_to_duration(seconds, user_data):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h: parts.append(f"{h} {t(user_data, 'time_hour')}")
    if m: parts.append(f"{m} {t(user_data, 'time_min')}")
    if s or not parts: parts.append(f"{s} {t(user_data, 'time_sec')}")
    return " ".join(parts)

def build_message(row, total_today_number, daily_income, cli_count, user_data):
    date_str = str(row[0]) if len(row) > 0 else "N/A"
    range_   = str(row[1]) if len(row) > 1 else "N/A"
    number   = str(row[2]) if len(row) > 2 else "N/A"
    cli      = str(row[3]) if len(row) > 3 else "N/A"
    sms_text = str(row[4]) if len(row) > 4 else "N/A"
    sms_text = sms_text.replace("$", "").strip()

    return (
        f"{t(user_data, 'new_sms')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{t(user_data, 'number')} : {number}\n"
        f"{t(user_data, 'range')}  : {range_}\n"
        f"{t(user_data, 'cli')}    : {cli}\n"
        f"{t(user_data, 'today')}  : {total_today_number} {t(user_data, 'sms_count')}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💬 {sms_text} [{cli_count}]\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🕐 {format_time(date_str)} | 💰 {daily_income:.4f}$"
    )

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [[{"text": "👨‍💻 Developer", "url": DEVELOPER}]]}
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error [{chat_id}]: {e}")

# ── Login ─────────────────────────────────────────────────────────────────────
def solve_captcha(soup):
    text = soup.get_text(" ", strip=True)
    match = re.search(r'(\d+)\s*([+\-])\s*(\d+)', text)
    if match:
        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
        return str(a + b if op == '+' else a - b)
    return "0"

def do_login(username, password):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    try:
        resp = session.get(f"{BASE_URL}/login", timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        captcha = solve_captcha(soup)

        resp = session.post(f"{BASE_URL}/signin", data={
            "username": username,
            "password": password,
            "capt": captcha
        }, timeout=15, allow_redirects=True)

        if "login" in resp.url.lower():
            print(f"❌ Login failed: {username}")
            return None

        print(f"✅ Login OK: {username}")
        session.headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE_URL}/client/SMSCDRStats",
            "Origin": BASE_URL,
        })
        return session
    except Exception as e:
        print(f"Login error [{username}]: {e}")
        return None

# ── SMS Check ─────────────────────────────────────────────────────────────────
def check_once(session, seen_ids):
    today = date.today().strftime("%Y-%m-%d")
    ajax_url = f"{BASE_URL}/client/res/data_smscdr.php"

    params = {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
        "frange": "", "fnum": "", "fcli": "",
        "fgdate": "", "fgmonth": "", "fgrange": "", "fgnumber": "", "fgcli": "",
        "fg": "0", "sEcho": "1", "iColumns": "7", "sColumns": ",,,,,,",
        "iDisplayStart": "0", "iDisplayLength": "2000",
        "mDataProp_0": "0", "mDataProp_1": "1", "mDataProp_2": "2",
        "mDataProp_3": "3", "mDataProp_4": "4", "mDataProp_5": "5", "mDataProp_6": "6",
        "sSearch": "", "bRegex": "false", "iSortCol_0": "0", "sSortDir_0": "desc",
        "iSortingCols": "1", "_": str(int(datetime.now().timestamp() * 1000))
    }

    try:
        r = session.get(ajax_url, params=params, timeout=20)
    except Exception as e:
        print(f"Request error: {e}")
        return seen_ids, False

    if r.status_code != 200:
        return seen_ids, False

    data = r.json()
    rows = data.get("aaData") or data.get("data") or []
    daily_income = calc_daily_income(rows)

    for row in rows:
        if isinstance(row, dict):
            row = list(row.values())
        if str(row[2]).strip() in ("0", "", "N/A"):
            continue
        row_id = "|".join(str(c) for c in row[:5])
        if row_id not in seen_ids:
            number = str(row[2]).strip()
            cli    = str(row[3]).strip()
            total_today_number = sum(
                1 for r in rows
                if str((list(r.values()) if isinstance(r, dict) else r)[2]).strip() == number
            )
            cli_count = get_cli_count_today(rows, cli)
            seen_ids.add(row_id)
            yield row, total_today_number, daily_income, cli_count

# ── Per-User Worker Thread ────────────────────────────────────────────────────
def user_worker(uid, user_data):
    tg_id     = user_data.get("tg_id") or uid
    username  = user_data.get("lamix_username", "")
    password  = user_data.get("lamix_password", "")
    seen_file = user_data.get("seen_file", f"seen_{uid}.json")

    if not username or not password:
        print(f"[{username}] credential নেই, skip।")
        return

    print(f"[{username}] শুরু হচ্ছে... (seen file: {seen_file})")
    session = do_login(username, password)

    if not session:
        send_telegram(tg_id, t(user_data, "login_failed"))
        return

    duration_str = seconds_to_duration(RUN_DURATION, user_data)

    send_telegram(tg_id, t(user_data, "sms_started", duration=duration_str))

    seen_ids = load_seen(seen_file)

    start_time = time.time()
    last_push  = time.time()
    loop_count = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed >= RUN_DURATION:
            print(f"[{username}] ১৯৫ মিনিট সম্পন্ন।")
            break

        loop_count += 1
        remaining = int(RUN_DURATION - elapsed)
        print(f"[{username}][{loop_count}] বাকি: {remaining//60}m {remaining%60}s")

        new_found = False
        try:
            for row, total, income, cli_count in check_once(session, seen_ids):
                send_telegram(tg_id, build_message(row, total, income, cli_count, user_data))
                new_found = True
        except Exception as e:
            print(f"[{username}] check error: {e}")

        if new_found or (time.time() - last_push >= 60):
            save_seen(seen_file, seen_ids)
            push_seen(seen_file)
            last_push = time.time()

        time.sleep(CHECK_INTERVAL)

    save_seen(seen_file, seen_ids)
    push_seen(seen_file)

    send_telegram(tg_id, t(user_data, "sms_stopped", duration=duration_str))

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists(USERS_FILE):
        print("❌ users.json পাওয়া যায়নি!")
        return

    with open(USERS_FILE) as f:
        users = json.load(f)

    for i in range(1, 51):
        secret_value = os.environ.get(f"USER{i}", "")
        if secret_value and "::" in secret_value:
            try:
                parts = secret_value.split("::")
                if len(parts) >= 3:
                    username = parts[0].strip()
                    password = parts[1].strip()
                    tg_id    = parts[2].strip()

                    if tg_id in users:
                        users[tg_id]["lamix_username"] = username
                        users[tg_id]["lamix_password"] = password
                    else:
                        users[tg_id] = {
                            "tg_id": tg_id,
                            "lamix_username": username,
                            "lamix_password": password,
                            "status": "approved",
                            "sms_on": True,
                            "language": "bn"
                        }
                    print(f"✅ USER{i} লোড সম্পন্ন: {username}")
            except Exception as e:
                print(f"❌ USER{i} লোডে error: {e}")

    threads = []

    approved_users = {
        uid: u for uid, u in users.items()
        if u.get("status") == "approved"
        and u.get("sms_on", False)
        and (
            not CURRENT_WORKFLOW
            or u.get("sms_workflow", "") == CURRENT_WORKFLOW
        )
    }

    if not approved_users:
        print(f"⚠️ [{CURRENT_WORKFLOW or 'default'}] কোনো active approved ইউজার নেই।")
        return

    print(f"✅ {len(approved_users)} জন ইউজারের জন্য thread শুরু হচ্ছে... (workflow: {CURRENT_WORKFLOW or 'all'})")

    for uid, user_data in approved_users.items():
        user_data["tg_id"] = uid
        th = threading.Thread(
            target=user_worker,
            args=(uid, user_data),
            daemon=True
        )
        th.start()
        threads.append(th)
        time.sleep(0.5)

    for th in threads:
        th.join()

    print("✅ সব thread সম্পন্ন।")

if __name__ == "__main__":
    main()
