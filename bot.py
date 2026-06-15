import os
import json
import requests
import time
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
TG_TOKEN     = os.environ["TELEGRAM_TOKEN"]
ADMIN_ID     = os.environ["ADMIN_CHAT_ID"]
GH_TOKEN     = os.environ["GH_PAT_TOKEN"]
GH_REPO      = os.environ["GH_REPO"]
LAMIX_URL    = os.environ["LAMIX_URL"]

USERS_FILE        = "users.json"
SMS_WORKFLOW      = "sms-check.yml"
VERIFY_WORKFLOW   = "verify.yml"
RUN_DURATION = 4 * 60 * 60 - 60

OFFSET = 0

WELCOME_TEXT = (
    "👋 <b>স্বাগতম!</b>\n"
    "━━━━━━━━━━━━━━━\n"
    "📩 এই বটের মাধ্যমে আপনি আপনার\n"
    "<b>LAMIX SMS</b> গুলো সহজে ও\n"
    "পার্সোনালি দেখতে পারবেন!\n\n"
    "✅ নতুন SMS আসলে সাথে সাথে\n"
    "   আপনার Telegram-এ নোটিফিকেশন\n\n"
    "✅ নিজের মতো চালু বা বন্ধ করুন\n\n"
    "✅ সম্পূর্ণ প্রাইভেট — শুধু আপনি দেখবেন\n"
    "━━━━━━━━━━━━━━━\n"
    "শুরু করতে নিচের বাটনে চাপুন 👇"
)

HELP_TEXT = (
    "📋 <b>কমান্ড লিস্ট:</b>\n"
    "━━━━━━━━━━━━━━━\n"
    "▶️ /sms_start — SMS চেকার চালু করুন\n"
    "⏹ /sms_stop  — SMS চেকার বন্ধ করুন\n"
    "📊 /status — বর্তমান অবস্থা দেখুন\n"
    "❓ /help  — এই মেনু দেখুন\n"
    "━━━━━━━━━━━━━━━"
)

ADMIN_HELP_TEXT = (
    "👑 <b>Admin কমান্ড লিস্ট</b>\n"
    "━━━━━━━━━━━━━━━\n"
    "▶️ /sms_start — SMS চেকার শুরু\n"
    "⏹ /sms_stop — SMS চেকার বন্ধ\n"
    "📊 /status — বর্তমান অবস্থা\n"
    "━━━━━━━━━━━━━━━\n"
    "👥 /users — সব ইউজার লিস্ট\n"
    "🔍 /user @username — ইউজারের পূর্ণ তথ্য\n"
    "✅ /approve @username sms-userX.yml\n"
    "🚫 /ban @username\n"
    "⏳ /pending @username\n"
    "🔄 /setwf @username sms-userX.yml\n"
    "📢 /notice <মেসেজ> — সব ইউজারকে নোটিস পাঠান\n"
    "━━━━━━━━━━━━━━━"
)

ADMIN_PANEL_TEXT = (
    "👑 <b>Admin Panel</b>\n"
    "━━━━━━━━━━━━━━━\n"
    "👥 /users — সব ইউজার লিস্ট\n"
    "🔍 /user @username — ইউজারের পূর্ণ তথ্য\n"
    "✅ /approve @username sms-userX.yml\n"
    "🚫 /ban @username\n"
    "⏳ /pending @username\n"
    "🔄 /setwf @username sms-userX.yml\n"
    "📢 /notice <মেসেজ> — সব ইউজারকে নোটিস\n"
    "▶️ /sms_start — SMS চেকার শুরু\n"
    "⏹ /sms_stop — SMS চেকার বন্ধ\n"
    "📊 /status — অবস্থা দেখুন\n"
    "❓ /help — কমান্ড লিস্ট\n"
    "━━━━━━━━━━━━━━━"
)

SUPPORT_MARKUP = {
    "inline_keyboard": [[
        {"text": "👨‍💼 Admin Support", "url": "https://t.me/Napa_Ex"}
    ]]
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def seconds_to_hms(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h:
        parts.append(f"{h} ঘন্টা")
    if m:
        parts.append(f"{m} মিনিট")
    if s or not parts:
        parts.append(f"{s} সেকেন্ড")
    return " ".join(parts)

def make_new_user_entry(username=""):
    return {
        "tg_username": username,
        "status": "new",
        "verify_status": "",
        "sms_on": False,
        "sms_workflow": "",
        "sms_start_time": "",
        "seen_file": "",
        "step": ""
    }

def get_user_guard(uid, users, chat_id):
    if uid not in users:
        markup = {"inline_keyboard": [[{"text": "🔗 একাউন্ট যোগ করুন", "callback_data": "link_account"}]]}
        send_message(chat_id,
            "⚠️ <b>একাউন্ট যোগ করা হয়নি!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "SMS চেকার ব্যবহার করতে\n"
            "আগে LAMIX একাউন্ট যোগ করুন।\n"
            "━━━━━━━━━━━━━━━\n"
            "নিচের বাটনে চাপুন 👇",
            markup
        )
        return True

    status = users[uid].get("status", "new")
    if status == "new":
        markup = {"inline_keyboard": [[{"text": "🔗 একাউন্ট যোগ করুন", "callback_data": "link_account"}]]}
        send_message(chat_id,
            "⚠️ <b>একাউন্ট যোগ করা হয়নি!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "SMS চেকার ব্যবহার করতে\n"
            "আগে LAMIX একাউন্ট যোগ করুন।\n"
            "━━━━━━━━━━━━━━━\n"
            "নিচের বাটনে চাপুন 👇",
            markup
        )
        return True
    elif status == "pending":
        send_message(chat_id,
            "⏳ <b>অনুমোদনের অপেক্ষায়</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার একাউন্ট যাচাই হয়েছে।\n"
            "Admin অনুমোদন করলেই শুরু করতে পারবেন।\n"
            "━━━━━━━━━━━━━━━\n"
            "⏳ অনুগ্রহ করে অপেক্ষা করুন।"
        )
        return True
    elif status == "banned":
        send_message(chat_id,
            "🚫 <b>আপনার একাউন্ট ব্যান করা হয়েছে।</b>\n"
            "বিস্তারিত জানতে Admin-এর সাথে যোগাযোগ করুন।"
        )
        return True
    return False

# ── Telegram Bot Command Menu Setup ───────────────────────────────────────────
USER_COMMANDS = [
    {"command": "start",     "description": "🏠 বট শুরু করুন / একাউন্ট যোগ করুন"},
    {"command": "sms_start", "description": "▶️ SMS চেকার চালু করুন — নতুন SMS আসলে নোটিফিকেশন পাবেন"},
    {"command": "sms_stop",  "description": "⏹ SMS চেকার বন্ধ করুন — নোটিফিকেশন বন্ধ হবে"},
    {"command": "status",    "description": "📊 SMS চেকার এখন চলছে কি না দেখুন"},
    {"command": "help",      "description": "❓ সব কমান্ডের তালিকা ও ব্যবহার দেখুন"},
]

ADMIN_COMMANDS = [
    {"command": "start",     "description": "🏠 Admin Panel খুলুন / একাউন্ট সেটআপ করুন"},
    {"command": "sms_start", "description": "▶️ নিজের SMS চেকার চালু করুন"},
    {"command": "sms_stop",  "description": "⏹ নিজের SMS চেকার বন্ধ করুন"},
    {"command": "status",    "description": "📊 SMS চেকারের বর্তমান অবস্থা দেখুন"},
    {"command": "help",      "description": "❓ সব কমান্ডের তালিকা দেখুন"},
    {"command": "users",     "description": "👥 সব রেজিস্টার্ড ইউজারের তালিকা দেখুন"},
    {"command": "user",      "description": "🔍 /user @username — ইউজারের পূর্ণ তথ্য দেখুন"},
    {"command": "approve",   "description": "✅ /approve @username sms-userX.yml — ইউজার অনুমোদন ও workflow সেট করুন"},
    {"command": "ban",       "description": "🚫 /ban @username — ইউজারকে ব্যান করুন"},
    {"command": "pending",   "description": "⏳ /pending @username — ইউজারকে pending অবস্থায় ফেরত পাঠান"},
    {"command": "setwf",     "description": "🔄 /setwf @username sms-userX.yml — ইউজারের GitHub workflow ফাইল সেট করুন"},
    {"command": "new",       "description": "🆕 /new @username — ইউজারকে রিসেট করুন, নতুন করে শুরু করতে পারবে"},
    {"command": "notice",    "description": "📢 /notice <মেসেজ> — সব ইউজারকে broadcast করুন"},
]

def setup_bot_commands():
    base_url = f"https://api.telegram.org/bot{TG_TOKEN}"
    requests.post(f"{base_url}/setMyCommands", json={
        "commands": USER_COMMANDS
    }, timeout=10)
    requests.post(f"{base_url}/setMyCommands", json={
        "commands": ADMIN_COMMANDS,
        "scope": {
            "type": "chat",
            "chat_id": int(ADMIN_ID)
        }
    }, timeout=10)

# ── Users DB ──────────────────────────────────────────────────────────────────
def load_users():
    os.system('git pull --rebase --autostash origin main 2>/dev/null || true')
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
        }
        clean_users[uid] = entry
    with open(USERS_FILE, "w") as f:
        json.dump(clean_users, f, indent=2, ensure_ascii=False)
    push_file(USERS_FILE)

def push_file(filename):
    os.system('git config user.email "action@github.com"')
    os.system('git config user.name "GitHub Action"')
    os.system(f'git add {filename}')
    os.system('git commit -m "chore: update users" || true')
    os.system('git push --force || true')

# ── Collect Old Users from Telegram History ───────────────────────────────────
def collect_old_users(users):
    """
    Telegram getUpdates দিয়ে পুরনো সব update স্ক্যান করে
    যেসব user আগে বটে মেসেজ দিয়েছে কিন্তু users.json এ নেই
    তাদের নতুন entry বানিয়ে সেভ করে।
    offset=0 দিয়ে শুরু করলে Telegram সর্বশেষ ~100 update দেয়।
    """
    url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
    added = 0
    try:
        # allowed_updates দিয়ে শুধু message নিই
        r = requests.get(url, params={"offset": 0, "limit": 100, "timeout": 10}, timeout=15)
        updates = r.json().get("result", [])
        for upd in updates:
            msg = upd.get("message", {})
            if not msg:
                cb = upd.get("callback_query", {})
                if cb:
                    from_info = cb.get("from", {})
                    uid = str(from_info.get("id", ""))
                    username = from_info.get("username", uid)
                    if uid and uid not in users:
                        users[uid] = make_new_user_entry(username)
                        added += 1
                continue
            from_info = msg.get("from", {})
            uid = str(from_info.get("id", ""))
            username = from_info.get("username", uid)
            if uid and uid not in users:
                users[uid] = make_new_user_entry(username)
                added += 1
    except Exception as e:
        print(f"[collect_old_users] error: {e}")

    if added > 0:
        save_users(users)
        print(f"[collect_old_users] {added} নতুন পুরনো ইউজার যোগ হয়েছে।")
    else:
        print("[collect_old_users] কোনো নতুন পুরনো ইউজার পাওয়া যায়নি।")

    return users

# ── Telegram ──────────────────────────────────────────────────────────────────
def get_updates(offset):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
    try:
        r = requests.get(url, params={"offset": offset, "timeout": 30}, timeout=35)
        return r.json().get("result", [])
    except:
        return []

def send_message(chat_id, text, reply_markup=None):
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
    except:
        pass

def answer_callback(callback_id, text=""):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_id, "text": text}, timeout=10)
    except:
        pass

# ── GitHub ────────────────────────────────────────────────────────────────────
def trigger_workflow(workflow, inputs=None):
    url = f"https://api.github.com/repos/{GH_REPO}/actions/workflows/{workflow}/dispatches"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    body = {"ref": "main"}
    if inputs:
        body["inputs"] = inputs
    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        return r.status_code == 204
    except:
        return False

def get_workflow_status(workflow):
    url = f"https://api.github.com/repos/{GH_REPO}/actions/workflows/{workflow}/runs"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        runs = r.json().get("workflow_runs", [])
        if not runs:
            return None, None
        latest = runs[0]
        return latest.get("status"), latest.get("id")
    except:
        return None, None

def cancel_workflow_run(run_id):
    url = f"https://api.github.com/repos/{GH_REPO}/actions/runs/{run_id}/cancel"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    try:
        r = requests.post(url, headers=headers, timeout=10)
        return r.status_code == 202
    except:
        return False

# ── Admin Notification ────────────────────────────────────────────────────────
def notify_admin_new_user(tg_id, tg_username, lamix_username, lamix_password):
    text = (
        f"🆕 <b>নতুন ইউজার যাচাই সম্পন্ন!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Telegram: @{tg_username}\n"
        f"🆔 ID: <code>{tg_id}</code>\n"
        f"🔑 LAMIX User: <code>{lamix_username}</code>\n"
        f"🔒 Password: <code>{lamix_password}</code>\n"
        f"✅ Login: সফল\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Approve করতে workflow নাম দিন:\n"
        f"/approve @{tg_username} sms-userX.yml"
    )
    markup = {
        "inline_keyboard": [[
            {"text": "🚫 Ban", "callback_data": f"ban|{tg_id}"}
        ]]
    }
    send_message(ADMIN_ID, text, markup)

# ── Format Message Handler (Admin Only) ──────────────────────────────────────
def handle_format_message(chat_id, user_id, text, users):
    if str(user_id) != str(ADMIN_ID):
        return False

    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if len(lines) != 3:
        return False
    if not lines[0].startswith("@"):
        return False

    target_username = lines[0][1:].lower()
    pass1 = lines[1]
    pass2 = lines[2]

    target_id = None
    for uid_key, u in users.items():
        if u.get("tg_username", "").lower() == target_username:
            target_id = uid_key
            break

    if not target_id:
        send_message(chat_id,
            f"❌ @{target_username} এর ID পাওয়া যায়নি।\n"
            f"সে আগে বটে /start দিয়েছে কি?"
        )
        return True

    result = f"USER1 = {pass1}::{pass2}::{target_id}"
    send_message(chat_id, f"<code>{result}</code>")
    return True

# ── Command Handlers ──────────────────────────────────────────────────────────
def handle_start(chat_id, user_id, username, users):
    uid = str(user_id)
    is_admin = uid == str(ADMIN_ID)

    if uid not in users:
        users[uid] = make_new_user_entry(username or "")
        save_users(users)

        if is_admin:
            markup = {
                "inline_keyboard": [[
                    {"text": "🔗 Admin একাউন্ট সেটআপ করুন", "callback_data": "link_account"}
                ]]
            }
            send_message(chat_id,
                "👑 <b>Admin Setup</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "প্রথমবার চালু হয়েছে!\n"
                "আপনার LAMIX credentials দিয়ে\n"
                "একাউন্ট সেটআপ করুন।\n"
                "━━━━━━━━━━━━━━━\n"
                "নিচের বাটনে চাপুন 👇",
                markup
            )
        else:
            markup = {
                "inline_keyboard": [[
                    {"text": "🔗 একাউন্ট যোগ করুন", "callback_data": "link_account"}
                ]]
            }
            send_message(chat_id, WELCOME_TEXT, markup)
        return users

    # username আপডেট করো যদি পরিবর্তন হয়ে থাকে
    if username and users[uid].get("tg_username") != username:
        users[uid]["tg_username"] = username
        save_users(users)

    status = users[uid].get("status", "new")

    if is_admin and status == "approved":
        send_message(chat_id, ADMIN_PANEL_TEXT)
        return users

    if not is_admin:
        if status == "new":
            markup = {"inline_keyboard": [[{"text": "🔗 একাউন্ট যোগ করুন", "callback_data": "link_account"}]]}
            send_message(chat_id,
                "⚠️ <b>একাউন্ট যোগ করা হয়নি!</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "SMS চেকার ব্যবহার করতে\n"
                "আগে আপনার LAMIX একাউন্ট যোগ করুন।\n"
                "━━━━━━━━━━━━━━━\n"
                "নিচের বাটনে চাপুন 👇",
                markup
            )
        elif status == "pending":
            send_message(chat_id,
                "⏳ <b>অনুমোদনের অপেক্ষায়</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "আপনার একাউন্ট যাচাই হয়েছে।\n"
                "Admin অনুমোদন করলেই শুরু করতে পারবেন।"
            )
        elif status == "banned":
            send_message(chat_id,
                "🚫 <b>আপনার একাউন্ট ব্যান করা হয়েছে।</b>\n"
                "বিস্তারিত জানতে Admin-এর সাথে যোগাযোগ করুন।"
            )
        elif status == "approved":
            send_message(chat_id,
                f"👋 স্বাগতম @{username}!\n"
                "━━━━━━━━━━━━━━━\n"
                "▶️ /sms_start — SMS চেকার চালু\n"
                "⏹ /sms_stop  — SMS চেকার বন্ধ\n"
                "📊 /status — অবস্থা দেখুন\n"
                "❓ /help — কমান্ড লিস্ট\n"
                "━━━━━━━━━━━━━━━"
            )
        return users

    if status == "new":
        markup = {"inline_keyboard": [[{"text": "🔗 Admin একাউন্ট সেটআপ করুন", "callback_data": "link_account"}]]}
        send_message(chat_id,
            "⚠️ <b>একাউন্ট যোগ করা হয়নি!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "নিচের বাটনে চাপুন 👇",
            markup
        )
    elif status == "pending":
        send_message(chat_id, "⏳ আপনার একাউন্ট verify হচ্ছে...")

    return users


# ── handle_sms_start ─────────────────────────────────────────────────────────
def handle_sms_start(chat_id, user_id, users):
    uid = str(user_id)
    is_admin = uid == str(ADMIN_ID)

    if uid not in users or users[uid].get("status") != "approved":
        get_user_guard(uid, users, chat_id)
        return users

    user_workflow = users[uid].get("sms_workflow", "")
    if not user_workflow:
        send_message(chat_id,
            "⚠️ <b>Workflow সেট করা হয়নি!</b>\n"
            + ("নিজে /setwf দিয়ে সেট করুন।" if is_admin else "Admin কে জানান। তিনি সেট করবেন।")
        )
        return users

    gh_status, _ = get_workflow_status(user_workflow)
    if gh_status in ("in_progress", "queued"):
        send_message(chat_id,
            "⚠️ <b>SMS চেকার ইতিমধ্যে চলছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "বন্ধ করতে /sms_stop দিন।"
        )
        return users

    if users[uid].get("sms_on") and gh_status not in ("in_progress", "queued"):
        users[uid]["sms_on"] = False

    send_message(chat_id, "⏳ SMS চেকার চালু করছি...")

    if trigger_workflow(user_workflow):
        users[uid]["sms_on"] = True
        users[uid]["sms_start_time"] = datetime.utcnow().isoformat()
        save_users(users)
    else:
        send_message(chat_id, "❌ চালু করা যায়নি। একটু পরে আবার চেষ্টা করুন।")
    return users


# ── handle_sms_stop ──────────────────────────────────────────────────────────
def handle_sms_stop(chat_id, user_id, users):
    uid = str(user_id)

    if uid not in users or users[uid].get("status") != "approved":
        get_user_guard(uid, users, chat_id)
        return users

    user_workflow = users[uid].get("sms_workflow", SMS_WORKFLOW)
    status, run_id = get_workflow_status(user_workflow)

    if status != "in_progress":
        if users[uid].get("sms_on"):
            users[uid]["sms_on"] = False
            users[uid]["sms_start_time"] = ""
            save_users(users)
        send_message(chat_id, "⚠️ এখন কোনো SMS চেকার চলছে না।")
        return users

    if cancel_workflow_run(run_id):
        users[uid]["sms_on"] = False
        users[uid]["sms_start_time"] = ""
        save_users(users)
        send_message(chat_id, "✅ SMS চেকার বন্ধ করা হয়েছে।")
    else:
        send_message(chat_id, "❌ বন্ধ করা যায়নি।")
    return users


# ── handle_status ────────────────────────────────────────────────────────────
def handle_status(chat_id, user_id, users):
    uid = str(user_id)

    if uid not in users or users[uid].get("status") != "approved":
        get_user_guard(uid, users, chat_id)
        return users

    user_workflow = users[uid].get("sms_workflow", SMS_WORKFLOW)
    gh_status, _ = get_workflow_status(user_workflow)

    if gh_status in ("in_progress", "queued"):
        sms_info = "🟢 চলছে"
        if not users[uid].get("sms_on"):
            users[uid]["sms_on"] = True
            save_users(users)
    elif gh_status == "completed":
        sms_info = "⚪ বন্ধ"
        if users[uid].get("sms_on"):
            users[uid]["sms_on"] = False
            users[uid]["sms_start_time"] = ""
            save_users(users)
    else:
        sms_info = "🔴 অজানা"

    remaining_str = ""
    if gh_status in ("in_progress", "queued"):
        start_time_str = users[uid].get("sms_start_time", "")
        if start_time_str:
            try:
                start_dt = datetime.fromisoformat(start_time_str)
                elapsed = (datetime.utcnow() - start_dt).total_seconds()
                worker_runtime = 195 * 60
                remaining = max(0, int(worker_runtime - elapsed))
                remaining_str = f"\n⏱ বাকি: {seconds_to_hms(remaining)}"
            except:
                pass

    send_message(chat_id,
        f"📊 <b>Status</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📩 SMS চেকার: {sms_info}{remaining_str}\n"
        f"━━━━━━━━━━━━━━━"
    )
    return users


def handle_users_list(chat_id, users):
    if not users:
        send_message(chat_id, "📋 কোনো ইউজার নেই।")
        return

    text = "👥 <b>ইউজার লিস্ট</b>\n━━━━━━━━━━━━━━━\n"
    for uid, u in users.items():
        status_icon = {"approved": "✅", "pending": "⏳", "banned": "🚫", "new": "🆕"}.get(u["status"], "❓")
        sms_icon = "🟢" if u.get("sms_on") else "🔴"
        text += (
            f"{status_icon} @{u.get('tg_username', 'N/A')}\n"
            f"   SMS: {sms_icon} | Verify: {u.get('verify_status', '❌')}\n"
            f"   ID: <code>{uid}</code>\n\n"
        )
    send_message(chat_id, text)


def handle_user_detail(chat_id, target_username, users):
    target_username = target_username.replace("@", "").lower()
    found = False
    for uid, u in users.items():
        if u.get("tg_username", "").lower() == target_username:
            found = True
            status_icon = {"approved": "✅", "pending": "⏳", "banned": "🚫", "new": "🆕"}.get(u.get("status", "new"), "❓")
            sms_icon = "🟢 চালু" if u.get("sms_on") else "🔴 বন্ধ"
            wf = u.get("sms_workflow", "") or "❌ সেট নেই"
            verify = u.get("verify_status", "") or "❌"
            seen_f = u.get("seen_file", "") or "❌ সেট নেই"

            text = (
                f"🔍 <b>ইউজার তথ্য</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 Telegram: @{u.get('tg_username', 'N/A')}\n"
                f"🆔 ID: <code>{uid}</code>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"✔️ Verify: {verify}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📋 Workflow: <code>{wf}</code>\n"
                f"📄 Seen File: <code>{seen_f}</code>\n"
                f"📩 SMS: {sms_icon}\n"
                f"{status_icon} Status: {u.get('status', 'new')}\n"
                f"━━━━━━━━━━━━━━━"
            )
            send_message(chat_id, text)
            break

    if not found:
        send_message(chat_id, f"❌ @{target_username} পাওয়া যায়নি।")

# ── Callback Handler ──────────────────────────────────────────────────────────
def handle_callback(callback, users):
    data    = callback["data"]
    cb_id   = callback["id"]
    from_id = str(callback["from"]["id"])
    chat_id = callback["message"]["chat"]["id"]

    if data == "link_account":
        answer_callback(cb_id)
        uid = from_id
        if uid not in users:
            username = callback["from"].get("username", str(from_id))
            users[uid] = make_new_user_entry(username)
        users[uid]["step"] = "await_username"
        save_users(users)
        send_message(chat_id,
            "🔑 <b>একাউন্ট যোগ করুন</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার <b>LAMIX Username</b> লিখুন:"
        )
        return users

    if from_id != str(ADMIN_ID):
        answer_callback(cb_id, "⚠️ শুধু Admin এই কাজ করতে পারবেন।")
        return users

    parts = data.split("|")
    if len(parts) != 2:
        answer_callback(cb_id, "❌ অজানা action।")
        return users

    action, target_id = parts

    if target_id not in users:
        answer_callback(cb_id, "ইউজার পাওয়া যায়নি।")
        return users

    if action == "approve":
        users[target_id]["status"] = "approved"
        save_users(users)
        answer_callback(cb_id, "✅ Approved!")
        send_message(int(target_id),
            "🎉 <b>আপনার একাউন্ট অনুমোদিত হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "এখন আপনি সব কমান্ড ব্যবহার করতে পারবেন।\n"
            "SMS চেকার চালু করতে /sms_start দিন।"
        )
    elif action == "ban":
        users[target_id]["status"] = "banned"
        save_users(users)
        answer_callback(cb_id, "🚫 Banned!")
        send_message(int(target_id),
            "🚫 <b>আপনার একাউন্ট ব্যান করা হয়েছে।</b>"
        )

    return users

# ── Step Handler ──────────────────────────────────────────────────────────────
def handle_step(chat_id, user_id, text, users):
    uid = str(user_id)
    is_admin = uid == str(ADMIN_ID)

    if uid not in users:
        return users

    step = users[uid].get("step", "")

    if step == "await_username":
        users[uid]["_temp_lamix_username"] = text.strip()
        users[uid]["step"] = "await_password"
        save_users(users)
        send_message(chat_id,
            "🔒 এখন আপনার <b>LAMIX Password</b> লিখুন:"
        )

    elif step == "await_password":
        lamix_username = users[uid].pop("_temp_lamix_username", "")
        lamix_password = text.strip()

        users[uid]["step"] = ""
        save_users(users)

        send_message(chat_id,
            "⏳ <b>একাউন্ট যাচাই করা হচ্ছে...</b>\n"
            "একটু অপেক্ষা করুন।"
        )

        triggered = trigger_workflow(VERIFY_WORKFLOW, {
            "user_id": uid,
            "lamix_username": lamix_username,
            "lamix_password": lamix_password
        })

        if not triggered:
            send_message(chat_id,
                "❌ <b>যাচাই শুরু করা যায়নি!</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "একটু পরে আবার চেষ্টা করুন। /start দিন।"
            )
            users[uid]["status"] = "new"
            users[uid]["step"] = ""
            save_users(users)

    return users


def handle_verify_result(user_id, success, lamix_username, lamix_password, users):
    uid = str(user_id)
    if uid not in users:
        return users

    tg_username = users[uid].get("tg_username", "")

    if success:
        users[uid]["status"] = "pending"
        users[uid]["verify_status"] = "done"
        users[uid]["step"] = ""
        save_users(users)
        send_message(int(uid),
            "✅ <b>যাচাই সম্পন্ন!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার তথ্য সঠিক আছে।\n"
            "Admin অনুমোদন করলেই আপনি\n"
            "SMS চেকার ব্যবহার করতে পারবেন।\n"
            "━━━━━━━━━━━━━━━\n"
            "⏳ অনুমোদনের অপেক্ষায় আছুন।"
        )
        notify_admin_new_user(uid, tg_username, lamix_username, lamix_password)

    else:
        if users[uid].get("status") == "pending":
            pass
        else:
            users[uid]["status"] = "new"
            users[uid]["verify_status"] = ""
        users[uid]["step"] = ""
        save_users(users)

        if users[uid].get("status") != "pending":
            send_message(int(uid),
                "❌ <b>একাউন্ট যাচাই ব্যর্থ হয়েছে!</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "Username বা Password ভুল হতে পারে।\n"
                "আবার চেষ্টা করতে /start দিন।"
            )

    return users

# ── Admin Text Commands ───────────────────────────────────────────────────────
def handle_admin_command(chat_id, text, users):
    parts = text.strip().split()
    cmd = parts[0].lower()

    if cmd == "/approve" and len(parts) >= 2:
        target_username = parts[1].replace("@", "").lower()
        workflow_name   = parts[2] if len(parts) >= 3 else ""
        seen_file       = workflow_name.replace(".yml", ".json") if workflow_name else ""
        found = False
        for uid, u in users.items():
            if u.get("tg_username", "").lower() == target_username:
                users[uid]["status"] = "approved"
                if workflow_name:
                    users[uid]["sms_workflow"] = workflow_name
                    users[uid]["seen_file"]    = seen_file
                save_users(users)
                wf_msg = f"\n📋 Workflow: <code>{workflow_name}</code>\n📄 Seen File: <code>{seen_file}</code>" if workflow_name else "\n⚠️ Workflow সেট হয়নি! /setwf দিয়ে সেট করুন।"
                send_message(chat_id, f"✅ @{target_username} কে approve করা হয়েছে।{wf_msg}")
                send_message(int(uid),
                    "🎉 <b>আপনার একাউন্ট অনুমোদিত হয়েছে!</b>\n"
                    "━━━━━━━━━━━━━━━\n"
                    "SMS চেকার চালু করতে /sms_start দিন।"
                )
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ @{target_username} পাওয়া যায়নি।")

    elif cmd == "/setwf" and len(parts) >= 3:
        target_username = parts[1].replace("@", "").lower()
        workflow_name   = parts[2]
        seen_file       = workflow_name.replace(".yml", ".json")
        found = False
        for uid, u in users.items():
            if u.get("tg_username", "").lower() == target_username:
                users[uid]["sms_workflow"] = workflow_name
                users[uid]["seen_file"]    = seen_file
                save_users(users)
                send_message(chat_id,
                    f"✅ @{target_username} এর workflow সেট হয়েছে।\n"
                    f"📋 Workflow: <code>{workflow_name}</code>\n"
                    f"📄 Seen File: <code>{seen_file}</code>"
                )
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ @{target_username} পাওয়া যায়নি।")

    elif cmd == "/ban" and len(parts) > 1:
        target_username = parts[1].replace("@", "").lower()
        found = False
        for uid, u in users.items():
            if u.get("tg_username", "").lower() == target_username:
                users[uid]["status"] = "banned"
                save_users(users)
                send_message(chat_id, f"🚫 @{target_username} কে ban করা হয়েছে।")
                send_message(int(uid), "🚫 <b>আপনার একাউন্ট ব্যান করা হয়েছে।</b>")
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ @{target_username} পাওয়া যায়নি।")

    elif cmd == "/pending" and len(parts) > 1:
        target_username = parts[1].replace("@", "").lower()
        found = False
        for uid, u in users.items():
            if u.get("tg_username", "").lower() == target_username:
                users[uid]["status"] = "pending"
                save_users(users)
                send_message(chat_id, f"⏳ @{target_username} কে pending করা হয়েছে।")
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ @{target_username} পাওয়া যায়নি।")

    elif cmd == "/users":
        handle_users_list(chat_id, users)

    elif cmd == "/user" and len(parts) > 1:
        handle_user_detail(chat_id, parts[1], users)

    elif cmd == "/new" and len(parts) > 1:
        target_username = parts[1].replace("@", "").lower()
        found = False
        for uid, u in users.items():
            if u.get("tg_username", "").lower() == target_username:
                users[uid]["status"] = "new"
                users[uid]["verify_status"] = ""
                users[uid]["sms_workflow"] = ""
                users[uid]["seen_file"] = ""
                users[uid]["sms_start_time"] = ""
                users[uid]["step"] = ""
                save_users(users)
                send_message(chat_id, f"🆕 @{target_username} কে new user করা হয়েছে।")
                send_message(int(uid),
                    "🔄 <b>আপনার একাউন্ট রিসেট করা হয়েছে।</b>\n"
                    "নতুনভাবে /start দিয়ে শুরু করুন।"
                )
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ @{target_username} পাওয়া যায়নি।")

    elif cmd == "/notice":
        # /notice এর পরে সব কিছুই মেসেজ
        notice_text = text[len("/notice"):].strip()
        if not notice_text:
            send_message(chat_id,
                "⚠️ মেসেজ লিখুন:\n"
                "/notice আপনার মেসেজ এখানে লিখুন"
            )
            return users

        success = 0
        failed = 0
        for uid in list(users.keys()):
            try:
                send_message(int(uid),
                    f"📢 <b>Admin Notice</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"{notice_text}\n"
                    f"━━━━━━━━━━━━━━━"
                )
                success += 1
            except:
                failed += 1
            time.sleep(0.1)  # Telegram rate limit এড়াতে

        send_message(chat_id,
            f"✅ <b>Notice পাঠানো হয়েছে!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✔️ সফল: {success} জন\n"
            f"❌ ব্যর্থ: {failed} জন"
        )

    return users

# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    global OFFSET
    start_time = time.time()
    users = load_users()

    setup_bot_commands()

    # ── পুরনো ইউজার collect করো — শুধুমাত্র users.json খালি থাকলে ──────────
    # চার ঘন্টা পরপর বট রিস্টার্ট হয়, কিন্তু users.json এ data থাকলে
    # আর খোঁজার দরকার নেই — শুধু প্রথমবার বা ফাইল খালি হলেই চালাবে
    if not users:
        users = collect_old_users(users)

    send_message(ADMIN_ID,
        "✅ <b>Bot চালু হয়েছে!</b>\n"
        "কমান্ড: /users, /approve @username sms-userX.yml, /ban @username\n"
        "📢 /notice <মেসেজ> — সব ইউজারকে broadcast করুন"
    )

    while True:
        if time.time() - start_time >= RUN_DURATION:
            send_message(ADMIN_ID, "⏰ Bot ৪ ঘন্টা সম্পন্ন। বন্ধ হচ্ছে।")
            break

        updates = get_updates(OFFSET)

        for update in updates:
            OFFSET = update["update_id"] + 1

            if "callback_query" in update:
                cb = update["callback_query"]
                users = handle_callback(cb, users)
                continue

            msg = update.get("message", {})
            if not msg:
                continue

            chat_id  = msg["chat"]["id"]
            user_id  = msg["from"]["id"]
            username = msg["from"].get("username", str(user_id))
            text     = msg.get("text", "").strip()

            if not text:
                continue

            # ── প্রতিটা message এ fresh data লোড করো ──────────────────────
            fresh = load_users()
            for _uid, _u in users.items():
                if "_temp_lamix_username" in _u:
                    if _uid in fresh:
                        fresh[_uid]["_temp_lamix_username"] = _u["_temp_lamix_username"]
            users = fresh
            # ────────────────────────────────────────────────────────────────

            uid      = str(user_id)
            is_admin = uid == str(ADMIN_ID)

            # ── নতুন ইউজার হলে এখানেই সেভ করো (message আসলে) ─────────────
            if uid not in users:
                users[uid] = make_new_user_entry(username or "")
                save_users(users)
            elif username and users[uid].get("tg_username") != username:
                users[uid]["tg_username"] = username
                save_users(users)
            # ────────────────────────────────────────────────────────────────

            if is_admin and any(
                text.lower().startswith(c) for c in [
                    "/approve", "/ban", "/pending", "/new",
                    "/users", "/setwf", "/user", "/notice"
                ]
            ):
                users = handle_admin_command(chat_id, text, users)
                continue

            if is_admin and handle_format_message(chat_id, user_id, text, users):
                continue

            if uid in users and users[uid].get("step", "") in ["await_username", "await_password"]:
                if not text.startswith("/"):
                    users = handle_step(chat_id, user_id, text, users)
                    continue

            if text == "/start":
                users = handle_start(chat_id, user_id, username, users)
            elif text == "/sms_start":
                users = handle_sms_start(chat_id, user_id, users)
            elif text in ("/sms_stop", "/stop"):
                users = handle_sms_stop(chat_id, user_id, users)
            elif text == "/status":
                users = handle_status(chat_id, user_id, users)
            elif text == "/help":
                if is_admin:
                    send_message(chat_id, ADMIN_HELP_TEXT, SUPPORT_MARKUP)
                else:
                    send_message(chat_id, HELP_TEXT, SUPPORT_MARKUP)
            else:
                if uid not in users or users[uid].get("status") != "approved":
                    get_user_guard(uid, users, chat_id)
                elif is_admin or users[uid].get("status") == "approved":
                    send_message(chat_id, "⚠️ অপরিচিত কমান্ড। /help দেখুন।")

        time.sleep(2)


if __name__ == "__main__":
    main()
