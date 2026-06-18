import requests
import json
import os
import re
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL   = os.environ["LAMIX_URL"]
TG_TOKEN   = os.environ["TELEGRAM_TOKEN"]
ADMIN_ID   = os.environ["ADMIN_CHAT_ID"]
USERS_FILE = "users.json"

USER_ID         = os.environ["INPUT_USER_ID"]
LAMIX_USERNAME  = os.environ["INPUT_LAMIX_USERNAME"]
LAMIX_PASSWORD  = os.environ["INPUT_LAMIX_PASSWORD"]

# ── Language Texts ────────────────────────────────────────────────────────────
TEXTS = {
    "bn": {
        "verify_success": (
            "✅ <b>একাউন্ট যাচাই সফল হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⏳ এখন Admin এর অনুমোদনের অপেক্ষায়।\n"
            "অনুমোদন হলে আপনাকে জানানো হবে।"
        ),
        "verify_failed": (
            "❌ <b>একাউন্ট যাচাই ব্যর্থ হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Username বা Password ভুল হতে পারে।\n"
            "আবার চেষ্টা করতে /start দিন।"
        ),
    },
    "en": {
        "verify_success": (
            "✅ <b>Account verification successful!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⏳ Waiting for Admin approval.\n"
            "You will be notified once approved."
        ),
        "verify_failed": (
            "❌ <b>Account verification failed!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Username or password may be wrong.\n"
            "Try again with /start."
        ),
    }
}

def get_text(users, uid, key):
    lang = users.get(uid, {}).get("language") or "bn"
    return TEXTS.get(lang, TEXTS["bn"]).get(key, TEXTS["bn"][key])

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

# ── Users DB ──────────────────────────────────────────────────────────────────
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}

def save_users(users):
    clean_users = {}
    for uid, u in users.items():
        entry = {
            "tg_username": u.get("tg_username", ""),
            "status": u.get("status", "new"),
            "verify_status": u.get("verify_status", ""),
            "sms_on": u.get("sms_on", False),
            "sms_workflow": u.get("sms_workflow", ""),
            "sms_start_time": u.get("sms_start_time", ""),
            "seen_file": u.get("seen_file", ""),
            "step": u.get("step", ""),
            "language": u.get("language") or "bn",  # ← language রিসেট হবে না
        }
        clean_users[uid] = entry
    with open(USERS_FILE, "w") as f:
        json.dump(clean_users, f, indent=2, ensure_ascii=False)
    push_file()

def push_file():
    os.system('git config user.email "action@github.com"')
    os.system('git config user.name "GitHub Action"')
    os.system(f'git add {USERS_FILE}')
    os.system('git commit -m "chore: update users" || true')
    os.system('git push --force || true')

# ── Login Verify ──────────────────────────────────────────────────────────────
def solve_captcha(soup):
    text = soup.get_text(" ", strip=True)
    match = re.search(r'(\d+)\s*([+\-])\s*(\d+)', text)
    if match:
        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
        return str(a + b if op == '+' else a - b)
    return "0"

def verify_login(username, password):
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
            return False

        return True

    except Exception as e:
        print(f"Login error: {e}")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"🔍 Verifying: {LAMIX_USERNAME}")

    users = load_users()
    success = verify_login(LAMIX_USERNAME, LAMIX_PASSWORD)

    if success:
        print(f"✅ Login সফল: {LAMIX_USERNAME}")

        if USER_ID in users:
            users[USER_ID]["status"] = "pending"
            users[USER_ID]["verify_status"] = "done"
            users[USER_ID]["step"] = ""
            # lamix credentials users.json এ সেভ হবে না
            save_users(users)

        # ইউজারের ভাষায় মেসেজ পাঠাও
        send_telegram(USER_ID, get_text(users, USER_ID, "verify_success"))

        # Admin কে notification পাঠাও (সবসময় বাংলায়)
        tg_username = users.get(USER_ID, {}).get("tg_username", USER_ID)
        markup = {
            "inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": f"approve|{USER_ID}"},
                {"text": "🚫 Ban", "callback_data": f"ban|{USER_ID}"}
            ]]
        }
        send_telegram(ADMIN_ID,
            f"🆕 <b>নতুন ইউজার যাচাই সম্পন্ন!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 Telegram: @{tg_username}\n"
            f"🆔 ID: <code>{USER_ID}</code>\n"
            f"🔑 LAMIX User: <code>{LAMIX_USERNAME}</code>\n"
            f"🔒 Password: <code>{LAMIX_PASSWORD}</code>\n"
            f"✅ Login: সফল\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Approve করতে:\n"
            f"/approve @{tg_username} sms-userX.yml",
            markup
        )

    else:
        print(f"❌ Login ব্যর্থ: {LAMIX_USERNAME}")

        if USER_ID in users:
            users[USER_ID]["status"] = "new"
            users[USER_ID]["step"] = ""
            users[USER_ID]["verify_status"] = ""
            save_users(users)

        # ইউজারের ভাষায় মেসেজ পাঠাও
        send_telegram(USER_ID, get_text(users, USER_ID, "verify_failed"))

if __name__ == "__main__":
    main()
