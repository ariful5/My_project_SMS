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

# verify.yml থেকে inputs হিসেবে আসবে
USER_ID         = os.environ["INPUT_USER_ID"]
LAMIX_USERNAME  = os.environ["INPUT_LAMIX_USERNAME"]
LAMIX_PASSWORD  = os.environ["INPUT_LAMIX_PASSWORD"]

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
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
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

    # Login check করো
    success = verify_login(LAMIX_USERNAME, LAMIX_PASSWORD)

    if success:
        print(f"✅ Login সফল: {LAMIX_USERNAME}")

        # users.json আপডেট করো (password ছাড়া)
        if USER_ID in users:
            users[USER_ID]["status"] = "pending"
            users[USER_ID]["lamix_username"] = LAMIX_USERNAME
            save_users(users)

        # ইউজারকে জানাও
        send_telegram(USER_ID,
            "✅ <b>একাউন্ট যাচাই সফল হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⏳ এখন Admin এর অনুমোদনের অপেক্ষায়।\n"
            "অনুমোদন হলে আপনাকে জানানো হবে।"
        )

        # Admin কে জানাও Approve/Ban বাটন সহ
        tg_username = users.get(USER_ID, {}).get("tg_username", "N/A")
        send_telegram(ADMIN_ID,
            f"🆕 <b>নতুন ইউজার যাচাই সম্পন্ন!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 Telegram: @{tg_username}\n"
            f"🆔 ID: <code>{USER_ID}</code>\n"
            f"🔑 LAMIX User: <code>{LAMIX_USERNAME}</code>\n"
            f"✅ Login: সফল\n"
            f"━━━━━━━━━━━━━━━",
            reply_markup={
                "inline_keyboard": [[
                    {"text": "✅ Approve", "callback_data": f"approve|{USER_ID}"},
                    {"text": "🚫 Ban",     "callback_data": f"ban|{USER_ID}"}
                ]]
            }
        )

    else:
        print(f"❌ Login ব্যর্থ: {LAMIX_USERNAME}")

        # users.json এ status new করো
        if USER_ID in users:
            users[USER_ID]["status"] = "new"
            users[USER_ID]["step"] = ""
            save_users(users)

        # ইউজারকে জানাও
        send_telegram(USER_ID,
            "❌ <b>একাউন্ট যাচাই ব্যর্থ হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Username বা Password ভুল হতে পারে।\n"
            "আবার চেষ্টা করতে /start দিন।"
        )

if __name__ == "__main__":
    main()
