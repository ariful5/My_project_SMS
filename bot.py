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
RUN_DURATION      = 4 * 60 * 60

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
    "▶️ /sms_start — SMS চেকার শুরু\n"
    "⏹ /sms_stop — SMS চেকার বন্ধ\n"
    "📊 /status — অবস্থা দেখুন\n"
    "❓ /help — কমান্ড লিস্ট\n"
    "━━━━━━━━━━━━━━━"
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def seconds_to_hms(seconds):
    """সেকেন্ডকে ঘন্টা মিনিট সেকেন্ড ফরম্যাটে রূপান্তর করে।"""
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
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}

def save_users(users):
    # ── users.json এ lamix_username এর বদলে verify_status থাকবে ──
    # password কখনো সেভ হবে না। verified হলে "done" লেখা থাকবে।
    # step field সেভ হবে না।
    clean_users = {}
    for uid, u in users.items():
        entry = {
            "tg_username": u.get("tg_username", ""),
            "status": u.get("status", "new"),
            "verify_status": u.get("verify_status", ""),  # "done" if verified
            "sms_on": u.get("sms_on", False),
            "sms_workflow": u.get("sms_workflow", ""),
            # step ইচ্ছাকৃতভাবে বাদ — শুধু runtime এ থাকে
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
    """
    শুধুমাত্র LAMIX credentials সঠিক হলে এই function call হবে।
    ভুল credentials এর ক্ষেত্রে এটা call হবে না।
    """
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
        users[uid] = {
            "tg_username": username or "",
            "status": "new",
            "verify_status": "",
            "sms_on": False,
            "sms_workflow": "",
            "step": ""
        }
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

    status = users[uid].get("status", "new")

    if is_admin and status == "approved":
        send_message(chat_id, ADMIN_PANEL_TEXT)
        return users

    if status == "new":
        btn_text = "🔗 Admin একাউন্ট সেটআপ করুন" if is_admin else "🔗 একাউন্ট যোগ করুন"
        markup = {
            "inline_keyboard": [[
                {"text": btn_text, "callback_data": "link_account"}
            ]]
        }
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
        if is_admin:
            send_message(chat_id, "⏳ আপনার একাউন্ট verify হচ্ছে...")
        else:
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


def handle_sms_start(chat_id, user_id, users):
    uid = str(user_id)
    is_admin = uid == str(ADMIN_ID)

    if uid not in users or users[uid].get("status") != "approved":
        if uid not in users or users[uid].get("status") == "new":
            markup = {"inline_keyboard": [[{"text": "🔗 একাউন্ট যোগ করুন", "callback_data": "link_account"}]]}
            send_message(chat_id, "⚠️ আগে LAMIX একাউন্ট যোগ করুন।", markup)
        elif users[uid].get("status") == "pending":
            send_message(chat_id, "⏳ আপনার একাউন্ট এখনো অনুমোদনের অপেক্ষায়।")
        elif users[uid].get("status") == "banned":
            send_message(chat_id, "🚫 আপনার একাউন্ট ব্যান করা হয়েছে।")
        return users

    user_workflow = users[uid].get("sms_workflow", "")
    if not user_workflow:
        send_message(chat_id,
            "⚠️ <b>Workflow সেট করা হয়নি!</b>\n"
            + ("নিজে /setwf দিয়ে সেট করুন।" if is_admin else "Admin কে জানান। তিনি সেট করবেন।")
        )
        return users

    send_message(chat_id, "⏳ SMS চেকার চালু করছি...")

    if trigger_workflow(user_workflow):
        users[uid]["sms_on"] = True
        save_users(users)
        # ── RUN_DURATION কে ঘন্টা মিনিট সেকেন্ডে দেখাও, workflow নাম লুকানো ──
        duration_str = seconds_to_hms(RUN_DURATION)
        send_message(chat_id,
            "✅ <b>SMS চেকার চালু হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"⏱ চলবে: {duration_str}\n"
            "🔄 চেক হবে: প্রতি ১ সেকেন্ডে\n"
            "━━━━━━━━━━━━━━━\n"
            "বন্ধ করতে /sms_stop দিন।"
        )
    else:
        send_message(chat_id, "❌ চালু করা যায়নি। একটু পরে আবার চেষ্টা করুন।")
    return users


def handle_sms_stop(chat_id, user_id, users):
    uid = str(user_id)

    if uid not in users or users[uid].get("status") != "approved":
        send_message(chat_id, "⚠️ আপনার একাউন্ট approved নয়।")
        return users

    user_workflow = users[uid].get("sms_workflow", SMS_WORKFLOW)
    status, run_id = get_workflow_status(user_workflow)

    if status != "in_progress":
        send_message(chat_id, "⚠️ এখন কোনো SMS চেকার চলছে না।")
        return users

    if cancel_workflow_run(run_id):
        users[uid]["sms_on"] = False
        save_users(users)
        send_message(chat_id, "✅ SMS চেকার বন্ধ করা হয়েছে।")
    else:
        send_message(chat_id, "❌ বন্ধ করা যায়নি।")
    return users


def handle_status(chat_id, user_id, users):
    uid = str(user_id)

    if uid not in users or users[uid].get("status") != "approved":
        send_message(chat_id, "⚠️ আপনার একাউন্ট approved নয়।")
        return users

    # ── Status এ workflow নাম দেখানো হবে না ──
    user_workflow = users[uid].get("sms_workflow", SMS_WORKFLOW)
    status, _ = get_workflow_status(user_workflow)

    if status == "in_progress":
        sms_info = "🟢 চলছে"
    elif status == "completed":
        sms_info = "⚪ বন্ধ"
    else:
        sms_info = "🔴 অজানা"

    send_message(chat_id,
        f"📊 <b>Status</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📩 SMS চেকার: {sms_info}\n"
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
        # ── /users এ workflow নাম দেখানো হবে না ──
        text += (
            f"{status_icon} @{u.get('tg_username', 'N/A')}\n"
            f"   SMS: {sms_icon} | Verify: {u.get('verify_status', '❌')}\n"
            f"   ID: <code>{uid}</code>\n\n"
        )
    send_message(chat_id, text)


def handle_user_detail(chat_id, target_username, users):
    """
    /user @username — Admin শুধুমাত্র এই কমান্ড দিয়ে
    একজন ইউজারের সব তথ্য দেখতে পারবেন:
    ID, LAMIX username, password (runtime এ থাকলে), workflow, SMS status।
    """
    target_username = target_username.replace("@", "").lower()
    found = False
    for uid, u in users.items():
        if u.get("tg_username", "").lower() == target_username:
            found = True
            status_icon = {"approved": "✅", "pending": "⏳", "banned": "🚫", "new": "🆕"}.get(u.get("status", "new"), "❓")
            sms_icon = "🟢 চালু" if u.get("sms_on") else "🔴 বন্ধ"
            wf = u.get("sms_workflow", "") or "❌ সেট নেই"
            lamix_user = u.get("lamix_username", "") or "❌ নেই"
            lamix_pass = u.get("lamix_password", "") or "❌ নেই"
            verify = u.get("verify_status", "") or "❌"

            text = (
                f"🔍 <b>ইউজার তথ্য</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 Telegram: @{u.get('tg_username', 'N/A')}\n"
                f"🆔 ID: <code>{uid}</code>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🔑 LAMIX User: <code>{lamix_user}</code>\n"
                f"🔒 Password: <code>{lamix_pass}</code>\n"
                f"✔️ Verify: {verify}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📋 Workflow: <code>{wf}</code>\n"
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
            users[uid] = {
                "tg_username": username,
                "status": "new",
                "verify_status": "",
                "sms_on": False,
                "sms_workflow": "",
                "step": ""
            }
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
        users[uid]["lamix_username"] = text.strip()
        users[uid]["step"] = "await_password"
        # ── username runtime এ রাখো, save করো না ──
        # save_users এখানে লাগবে না; step পরিবর্তন runtime এই থাকুক
        send_message(chat_id,
            "🔒 এখন আপনার <b>LAMIX Password</b> লিখুন:"
        )

    elif step == "await_password":
        lamix_username = users[uid].get("lamix_username", "")
        lamix_password = text.strip()

        # ── password runtime এ রাখো, verification পরে verify workflow জানাবে ──
        users[uid]["lamix_password"] = lamix_password
        users[uid]["step"] = "verifying"

        send_message(chat_id,
            "⏳ <b>একাউন্ট যাচাই করা হচ্ছে...</b>\n"
            "একটু অপেক্ষা করুন।"
        )

        triggered = trigger_workflow(VERIFY_WORKFLOW, {
            "user_id": uid,
            "lamix_username": lamix_username,
            "lamix_password": lamix_password
        })

        if triggered:
            if is_admin:
                # ── Admin self-approve: verify trigger হলেই approved ──
                users[uid]["status"] = "approved"
                users[uid]["verify_status"] = "done"
                users[uid]["step"] = ""
                # password সেভ করা হবে না
                del users[uid]["lamix_password"]
                users[uid]["lamix_username"] = ""
                save_users(users)
                send_message(chat_id,
                    "🎉 <b>Admin একাউন্ট সেটআপ সম্পন্ন!</b>\n"
                    "━━━━━━━━━━━━━━━\n"
                    f"🔑 LAMIX User: <code>{lamix_username}</code>\n"
                    "✅ আপনি এখন approved!\n"
                    "━━━━━━━━━━━━━━━\n"
                    "⚠️ এখন workflow সেট করুন:\n"
                    f"/setwf @{users[uid].get('tg_username', '')} sms-check.yml\n"
                    "━━━━━━━━━━━━━━━\n"
                    "তারপর /sms_start দিয়ে শুরু করুন।"
                )
            else:
                # ── Regular user: এখনই "যাচাই সম্পন্ন" দেখাবে না ──
                # verify workflow শেষ হলে আলাদা endpoint বা webhook জানাবে।
                # এখানে শুধু "যাচাই চলছে" দেখাই। Admin notification পরে যাবে।
                # (verify.yml এর result এলে handle_verify_result call হবে)
                users[uid]["status"] = "verifying"
                users[uid]["step"] = ""
                save_users(users)
                send_message(chat_id,
                    "⏳ <b>যাচাই চলছে...</b>\n"
                    "━━━━━━━━━━━━━━━\n"
                    "আপনার তথ্য যাচাই হচ্ছে।\n"
                    "সঠিক হলে Admin এর কাছে\n"
                    "অনুমোদনের জন্য পাঠানো হবে।\n"
                    "একটু অপেক্ষা করুন।"
                )
        else:
            # ── Workflow trigger ই হয়নি — সরাসরি error ──
            send_message(chat_id,
                "❌ <b>একাউন্ট যাচাই ব্যর্থ হয়েছে!</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "Username বা Password ভুল হতে পারে।\n"
                "আবার চেষ্টা করতে /start দিন।"
            )
            users[uid]["status"] = "new"
            users[uid]["step"] = ""
            if "lamix_password" in users[uid]:
                del users[uid]["lamix_password"]
            users[uid]["lamix_username"] = ""
            save_users(users)

    return users


def handle_verify_result(user_id, success, lamix_username, lamix_password, users):
    """
    verify.yml workflow শেষ হলে এই function call করতে হবে।
    success=True  → Admin কে notify করো, user কে "অনুমোদনের অপেক্ষায়" বলো।
    success=False → User কে error দেখাও, status=new করো। Admin কে কিছু পাঠাবে না।
    """
    uid = str(user_id)
    if uid not in users:
        return users

    tg_username = users[uid].get("tg_username", "")

    if success:
        # ── শুধু সফল হলে admin notification ──
        users[uid]["status"] = "pending"
        users[uid]["verify_status"] = "done"
        users[uid]["lamix_username"] = ""  # সেভ করবো না
        if "lamix_password" in users[uid]:
            del users[uid]["lamix_password"]
        save_users(users)

        # User কে সফল বার্তা
        send_message(int(uid),
            "✅ <b>যাচাই সম্পন্ন!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Admin অনুমোদন করলে SMS চেকার\n"
            "ব্যবহার করতে পারবেন।\n"
            "একটু অপেক্ষা করুন।"
        )

        # Admin কে notify করো (শুধু সফল হলে)
        notify_admin_new_user(uid, tg_username, lamix_username, lamix_password)

    else:
        # ── ব্যর্থ হলে শুধু user কে জানাও, admin কে না ──
        users[uid]["status"] = "new"
        users[uid]["step"] = ""
        users[uid]["verify_status"] = ""
        users[uid]["lamix_username"] = ""
        if "lamix_password" in users[uid]:
            del users[uid]["lamix_password"]
        save_users(users)

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
        found = False
        for uid, u in users.items():
            if u.get("tg_username", "").lower() == target_username:
                users[uid]["status"] = "approved"
                if workflow_name:
                    users[uid]["sms_workflow"] = workflow_name
                save_users(users)
                wf_msg = f"\n📋 Workflow সেট হয়েছে।" if workflow_name else "\n⚠️ Workflow সেট হয়নি! /setwf দিয়ে সেট করুন।"
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
        found = False
        for uid, u in users.items():
            if u.get("tg_username", "").lower() == target_username:
                users[uid]["sms_workflow"] = workflow_name
                save_users(users)
                # ── workflow নাম শুধু admin কে confirm এ দেখাও ──
                send_message(chat_id,
                    f"✅ @{target_username} এর workflow সেট হয়েছে।"
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
        # ── /user @username — ইউজারের পূর্ণ তথ্য Admin দেখবেন ──
        handle_user_detail(chat_id, parts[1], users)

    elif cmd == "/new" and len(parts) > 1:
        target_username = parts[1].replace("@", "").lower()
        found = False
        for uid, u in users.items():
            if u.get("tg_username", "").lower() == target_username:
                users[uid]["status"] = "new"
                users[uid]["lamix_username"] = ""
                users[uid]["verify_status"] = ""
                users[uid]["sms_workflow"] = ""
                users[uid]["step"] = ""
                if "lamix_password" in users[uid]:
                    del users[uid]["lamix_password"]
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

    return users

# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    global OFFSET
    start_time = time.time()
    users = load_users()

    setup_bot_commands()

    send_message(ADMIN_ID,
        "✅ <b>Bot চালু হয়েছে!</b>\n"
        "কমান্ড: /users, /approve @username sms-userX.yml, /ban @username"
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

            uid      = str(user_id)
            is_admin = uid == str(ADMIN_ID)

            if is_admin and any(
                text.lower().startswith(c) for c in ["/approve", "/ban", "/pending", "/new", "/users", "/setwf", "/user"]
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
                    send_message(chat_id, ADMIN_HELP_TEXT)
                else:
                    send_message(chat_id, HELP_TEXT)
            else:
                if is_admin or (uid in users and users[uid].get("status") == "approved"):
                    send_message(chat_id, "⚠️ অপরিচিত কমান্ড। /help দেখুন।")

        time.sleep(2)


if __name__ == "__main__":
    main()
