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
LANG_FILE         = "lang.json"  # language পার্মানেন্ট সেভ করার জন্য
SMS_WORKFLOW      = "sms-check.yml"
VERIFY_WORKFLOW   = "verify.yml"
RUN_DURATION = 4 * 60 * 60 - 60

OFFSET = 0

# ── Language Texts ────────────────────────────────────────────────────────────
TEXTS = {
    "bn": {
        "welcome": (
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
        ),
        "help": (
            "📋 <b>কমান্ড লিস্ট:</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "▶️ /sms_start — SMS চেকার চালু করুন\n"
            "⏹ /sms_stop  — SMS চেকার বন্ধ করুন\n"
            "📊 /status — বর্তমান অবস্থা দেখুন\n"
            "🌐 /language — ভাষা পরিবর্তন করুন\n"
            "❓ /help  — এই মেনু দেখুন\n"
            "━━━━━━━━━━━━━━━"
        ),
        "language_prompt": (
            "🌐 <b>ভাষা নির্বাচন করুন</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার পছন্দের ভাষা বেছে নিন:"
        ),
        "language_set": "✅ ভাষা বাংলায় সেট করা হয়েছে।",
        "link_account": "🔗 একাউন্ট যোগ করুন",
        "enter_username": (
            "🔑 <b>একাউন্ট যোগ করুন</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার <b>LAMIX Username</b> লিখুন:"
        ),
        "enter_password": "🔒 এখন আপনার <b>LAMIX Password</b> লিখুন:",
        "verifying": "⏳ <b>একাউন্ট যাচাই করা হচ্ছে...</b>\nএকটু অপেক্ষা করুন।",
        "verify_failed_trigger": (
            "❌ <b>যাচাই শুরু করা যায়নি!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "একটু পরে আবার চেষ্টা করুন। /start দিন।"
        ),
        "verify_success": (
            "✅ <b>যাচাই সম্পন্ন!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার তথ্য সঠিক আছে।\n"
            "Admin অনুমোদন করলেই আপনি\n"
            "SMS চেকার ব্যবহার করতে পারবেন।\n"
            "━━━━━━━━━━━━━━━\n"
            "⏳ অনুমোদনের অপেক্ষায় আছুন।"
        ),
        "verify_failed": (
            "❌ <b>একাউন্ট যাচাই ব্যর্থ হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Username বা Password ভুল হতে পারে।\n"
            "আবার চেষ্টা করতে /start দিন।"
        ),
        "approved_notice": (
            "🎉 <b>আপনার একাউন্ট অনুমোদিত হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "SMS চেকার চালু করতে /sms_start দিন।"
        ),
        "banned_notice": "🚫 <b>আপনার একাউন্ট ব্যান করা হয়েছে।</b>",
        "reset_notice": (
            "🔄 <b>আপনার একাউন্ট রিসেট করা হয়েছে।</b>\n"
            "নতুনভাবে /start দিয়ে শুরু করুন।"
        ),
        "not_registered": (
            "⚠️ <b>একাউন্ট যোগ করা হয়নি!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "SMS চেকার ব্যবহার করতে\n"
            "আগে LAMIX একাউন্ট যোগ করুন।\n"
            "━━━━━━━━━━━━━━━\n"
            "নিচের বাটনে চাপুন 👇"
        ),
        "pending_msg": (
            "⏳ <b>অনুমোদনের অপেক্ষায়</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার একাউন্ট যাচাই হয়েছে।\n"
            "Admin অনুমোদন করলেই শুরু করতে পারবেন।\n"
            "━━━━━━━━━━━━━━━\n"
            "⏳ অনুগ্রহ করে অপেক্ষা করুন।"
        ),
        "banned_msg": (
            "🚫 <b>আপনার একাউন্ট ব্যান করা হয়েছে।</b>\n"
            "বিস্তারিত জানতে Admin-এর সাথে যোগাযোগ করুন।"
        ),
        "sms_already_on": (
            "⚠️ <b>SMS চেকার ইতিমধ্যে চলছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "বন্ধ করতে /sms_stop দিন।"
        ),
        "sms_starting": "⏳ SMS চেকার চালু করছি...",
        "sms_start_failed": "❌ চালু করা যায়নি। একটু পরে আবার চেষ্টা করুন।",
        "sms_not_running": "⚠️ এখন কোনো SMS চেকার চলছে না।",
        "sms_stopped": "✅ SMS চেকার বন্ধ করা হয়েছে।",
        "sms_stop_failed": "❌ বন্ধ করা যায়নি।",
        "no_workflow": "⚠️ <b>Workflow সেট করা হয়নি!</b>",
        "unknown_cmd": "⚠️ অপরিচিত কমান্ড। /help দেখুন।",
        "welcome_back": (
            "👋 স্বাগতম @{username}!\n"
            "━━━━━━━━━━━━━━━\n"
            "▶️ /sms_start — SMS চেকার চালু\n"
            "⏹ /sms_stop  — SMS চেকার বন্ধ\n"
            "📊 /status — অবস্থা দেখুন\n"
            "🌐 /language — ভাষা পরিবর্তন\n"
            "❓ /help — কমান্ড লিস্ট\n"
            "━━━━━━━━━━━━━━━"
        ),
        "status_title": "📊 <b>Status</b>",
        "status_on": "🟢 চলছে",
        "status_off": "⚪ বন্ধ",
        "status_unknown": "🔴 অজানা",
        "remaining": "⏱ বাকি",
        "sms_checker": "📩 SMS চেকার",
        "time_hour": "ঘন্টা",
        "time_min": "মিনিট",
        "time_sec": "সেকেন্ড",
    },
    "en": {
        "welcome": (
            "👋 <b>Welcome!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "📩 With this bot you can easily\n"
            "view your <b>LAMIX SMS</b> privately!\n\n"
            "✅ Get notified instantly on Telegram\n"
            "   when a new SMS arrives\n\n"
            "✅ Start or stop anytime you want\n\n"
            "✅ Completely private — only you can see\n"
            "━━━━━━━━━━━━━━━\n"
            "Tap the button below to get started 👇"
        ),
        "help": (
            "📋 <b>Command List:</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "▶️ /sms_start — Start SMS checker\n"
            "⏹ /sms_stop  — Stop SMS checker\n"
            "📊 /status — View current status\n"
            "🌐 /language — Change language\n"
            "❓ /help  — Show this menu\n"
            "━━━━━━━━━━━━━━━"
        ),
        "language_prompt": (
            "🌐 <b>Select Language</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Choose your preferred language:"
        ),
        "language_set": "✅ Language set to English.",
        "link_account": "🔗 Link Account",
        "enter_username": (
            "🔑 <b>Link Account</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Enter your <b>LAMIX Username</b>:"
        ),
        "enter_password": "🔒 Now enter your <b>LAMIX Password</b>:",
        "verifying": "⏳ <b>Verifying your account...</b>\nPlease wait.",
        "verify_failed_trigger": (
            "❌ <b>Verification could not start!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Try again later. Send /start."
        ),
        "verify_success": (
            "✅ <b>Verification complete!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Your credentials are correct.\n"
            "You can use the SMS checker\n"
            "once the Admin approves your account.\n"
            "━━━━━━━━━━━━━━━\n"
            "⏳ Please wait for approval."
        ),
        "verify_failed": (
            "❌ <b>Account verification failed!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Username or password may be wrong.\n"
            "Try again with /start."
        ),
        "approved_notice": (
            "🎉 <b>Your account has been approved!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Use /sms_start to start the SMS checker."
        ),
        "banned_notice": "🚫 <b>Your account has been banned.</b>",
        "reset_notice": (
            "🔄 <b>Your account has been reset.</b>\n"
            "Start fresh with /start."
        ),
        "not_registered": (
            "⚠️ <b>Account not linked!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Please link your LAMIX account\n"
            "before using the SMS checker.\n"
            "━━━━━━━━━━━━━━━\n"
            "Tap the button below 👇"
        ),
        "pending_msg": (
            "⏳ <b>Awaiting Approval</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Your account has been verified.\n"
            "You can start once the Admin approves.\n"
            "━━━━━━━━━━━━━━━\n"
            "⏳ Please wait."
        ),
        "banned_msg": (
            "🚫 <b>Your account has been banned.</b>\n"
            "Contact Admin for more info."
        ),
        "sms_already_on": (
            "⚠️ <b>SMS checker is already running!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "Use /sms_stop to stop it."
        ),
        "sms_starting": "⏳ Starting SMS checker...",
        "sms_start_failed": "❌ Could not start. Please try again later.",
        "sms_not_running": "⚠️ No SMS checker is currently running.",
        "sms_stopped": "✅ SMS checker has been stopped.",
        "sms_stop_failed": "❌ Could not stop.",
        "no_workflow": "⚠️ <b>Workflow not set!</b>",
        "unknown_cmd": "⚠️ Unknown command. See /help.",
        "welcome_back": (
            "👋 Welcome @{username}!\n"
            "━━━━━━━━━━━━━━━\n"
            "▶️ /sms_start — Start SMS checker\n"
            "⏹ /sms_stop  — Stop SMS checker\n"
            "📊 /status — View status\n"
            "🌐 /language — Change language\n"
            "❓ /help — Command list\n"
            "━━━━━━━━━━━━━━━"
        ),
        "status_title": "📊 <b>Status</b>",
        "status_on": "🟢 Running",
        "status_off": "⚪ Stopped",
        "status_unknown": "🔴 Unknown",
        "remaining": "⏱ Remaining",
        "sms_checker": "📩 SMS Checker",
        "time_hour": "hr",
        "time_min": "min",
        "time_sec": "sec",
    }
}

ADMIN_HELP_TEXT = (
    "👑 <b>Admin কমান্ড লিস্ট</b>\n"
    "━━━━━━━━━━━━━━━\n"
    "▶️ /sms_start — SMS চেকার শুরু\n"
    "⏹ /sms_stop — SMS চেকার বন্ধ\n"
    "📊 /status — বর্তমান অবস্থা\n"
    "🌐 /language — ভাষা পরিবর্তন\n"
    "━━━━━━━━━━━━━━━\n"
    "👥 /users — সব ইউজার লিস্ট\n"
    "🔍 /user @username — ইউজারের পূর্ণ তথ্য\n"
    "✅ /approve @username sms-userX.yml\n"
    "🚫 /ban @username\n"
    "⏳ /pending @username\n"
    "🔄 /setwf @username sms-userX.yml\n"
    "📢 /notice <মেসেজ> — সব ইউজারকে নোটিস\n"
    "📢 /notice @username <মেসেজ> — নির্দিষ্ট ইউজারকে নোটিস\n"
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
    "📢 /notice @username <মেসেজ> — নির্দিষ্ট ইউজারকে নোটিস\n"
    "▶️ /sms_start — SMS চেকার শুরু\n"
    "⏹ /sms_stop — SMS চেকার বন্ধ\n"
    "📊 /status — অবস্থা দেখুন\n"
    "🌐 /language — ভাষা পরিবর্তন\n"
    "❓ /help — কমান্ড লিস্ট\n"
    "━━━━━━━━━━━━━━━"
)

SUPPORT_MARKUP = {
    "inline_keyboard": [[
        {"text": "👨‍💼 Admin Support", "url": "https://t.me/Napa_Ex"}
    ]]
}

# ── Language Helper ───────────────────────────────────────────────────────────
def get_lang(users, uid):
    """ইউজারের ভাষা রিটার্ন করে, ডিফল্ট বাংলা"""
    if uid in users:
        lang = users[uid].get("language", "")
        if lang in ("bn", "en"):
            return lang
    return "bn"

def t(users, uid, key, **kwargs):
    """ভাষা অনুযায়ী টেক্সট রিটার্ন করে"""
    lang = get_lang(users, uid)
    text = TEXTS.get(lang, TEXTS["bn"]).get(key, TEXTS["bn"].get(key, ""))
    if kwargs:
        text = text.format(**kwargs)
    return text

# ── Helpers ───────────────────────────────────────────────────────────────────
def seconds_to_hms(seconds, lang="bn"):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    txt = TEXTS.get(lang, TEXTS["bn"])
    parts = []
    if h:
        parts.append(f"{h} {txt['time_hour']}")
    if m:
        parts.append(f"{m} {txt['time_min']}")
    if s or not parts:
        parts.append(f"{s} {txt['time_sec']}")
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
        "step": "",
        "language": ""   # খালি = ভাষা এখনো সিলেক্ট হয়নি
    }

def get_user_guard(uid, users, chat_id):
    lang = get_lang(users, uid)
    if uid not in users:
        markup = {"inline_keyboard": [[{"text": TEXTS[lang]["link_account"], "callback_data": "link_account"}]]}
        send_message(chat_id, TEXTS[lang]["not_registered"], markup)
        return True

    status = users[uid].get("status", "new")
    if status == "new":
        markup = {"inline_keyboard": [[{"text": TEXTS[lang]["link_account"], "callback_data": "link_account"}]]}
        send_message(chat_id, TEXTS[lang]["not_registered"], markup)
        return True
    elif status == "pending":
        send_message(chat_id, TEXTS[lang]["pending_msg"])
        return True
    elif status == "banned":
        send_message(chat_id, TEXTS[lang]["banned_msg"])
        return True
    return False

# ── Language Selection Keyboard ───────────────────────────────────────────────
def language_keyboard():
    return {
        "inline_keyboard": [[
            {"text": "🇧🇩 বাংলা", "callback_data": "set_lang|bn"},
            {"text": "🇬🇧 English", "callback_data": "set_lang|en"}
        ]]
    }

# ── Telegram Bot Command Menu Setup ───────────────────────────────────────────
USER_COMMANDS = [
    {"command": "start",     "description": "🏠 বট শুরু / Start bot"},
    {"command": "sms_start", "description": "▶️ SMS চেকার চালু / Start SMS checker"},
    {"command": "sms_stop",  "description": "⏹ SMS চেকার বন্ধ / Stop SMS checker"},
    {"command": "status",    "description": "📊 অবস্থা দেখুন / View status"},
    {"command": "language",  "description": "🌐 ভাষা পরিবর্তন / Change language"},
    {"command": "help",      "description": "❓ কমান্ড লিস্ট / Command list"},
]

ADMIN_COMMANDS = [
    {"command": "start",     "description": "🏠 Admin Panel / একাউন্ট সেটআপ"},
    {"command": "sms_start", "description": "▶️ SMS চেকার চালু"},
    {"command": "sms_stop",  "description": "⏹ SMS চেকার বন্ধ"},
    {"command": "status",    "description": "📊 SMS চেকারের অবস্থা"},
    {"command": "language",  "description": "🌐 ভাষা পরিবর্তন"},
    {"command": "help",      "description": "❓ সব কমান্ড দেখুন"},
    {"command": "users",     "description": "👥 সব ইউজার লিস্ট"},
    {"command": "user",      "description": "🔍 /user @username — ইউজার তথ্য"},
    {"command": "approve",   "description": "✅ /approve @username sms-userX.yml"},
    {"command": "ban",       "description": "🚫 /ban @username"},
    {"command": "pending",   "description": "⏳ /pending @username"},
    {"command": "setwf",     "description": "🔄 /setwf @username sms-userX.yml"},
    {"command": "new",       "description": "🆕 /new @username — ইউজার রিসেট"},
    {"command": "notice",    "description": "📢 /notice [মেসেজ] বা /notice @username [মেসেজ]"},
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
            data = json.load(f)
        # lang store থেকে language restore করো (race condition এ হারিয়ে গেলেও ফেরত পাবে)
        lang_store = load_lang_store()
        for uid, u in data.items():
            if "language" not in u or u.get("language") not in ("bn", "en", ""):
                u["language"] = ""
            # lang store এ valid language থাকলে সেটাই ব্যবহার করো
            if uid in lang_store and lang_store[uid] in ("bn", "en"):
                u["language"] = lang_store[uid]
        return data
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
            "language": u.get("language", "") if u.get("language") in ("bn", "en", "") else "",
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
    # push retry: একবার fail হলে pull করে আবার push
    ret = os.system('git push --force 2>/dev/null')
    if ret != 0:
        os.system('git pull --rebase --autostash origin main 2>/dev/null || true')
        os.system('git push --force || true')

# ── Language Persistence ─────────────────────────────────────────────────────
def load_lang_store():
    """language আলাদা ফাইলে সেভ থাকে যাতে users.json race condition এ হারিয়ে না যায়"""
    try:
        if os.path.exists(LANG_FILE):
            with open(LANG_FILE) as f:
                data = json.load(f)
                # শুধু language field গুলো রিটার্ন করো
                return {uid: v for uid, v in data.items() if isinstance(v, str) and v in ("bn", "en")}
    except:
        pass
    return {}

def save_lang_store(users):
    """সব ইউজারের language আলাদা file এ সেভ করো"""
    try:
        lang_data = {}
        if os.path.exists(LANG_FILE):
            with open(LANG_FILE) as f:
                lang_data = json.load(f)
    except:
        lang_data = {}
    for uid, u in users.items():
        lang = u.get("language", "")
        if lang in ("bn", "en"):
            lang_data[uid] = lang
    with open(LANG_FILE, "w") as f:
        json.dump(lang_data, f, indent=2, ensure_ascii=False)
    # এই ফাইলও push করো
    os.system(f'git add {LANG_FILE}')
    os.system('git commit -m "chore: update lang" || true')
    ret = os.system('git push --force 2>/dev/null')
    if ret != 0:
        os.system('git pull --rebase --autostash origin main 2>/dev/null || true')
        os.system('git push --force || true')

# ── Collect Old Users ─────────────────────────────────────────────────────────
def collect_old_users(users):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
    added = 0
    try:
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

# ── Language Command Handler ──────────────────────────────────────────────────
def handle_language(chat_id, user_id, users):
    uid = str(user_id)
    lang = get_lang(users, uid)
    send_message(chat_id, TEXTS[lang]["language_prompt"], language_keyboard())

# ── Command Handlers ──────────────────────────────────────────────────────────
def handle_start(chat_id, user_id, username, users):
    uid = str(user_id)
    is_admin = uid == str(ADMIN_ID)

    if uid not in users:
        users[uid] = make_new_user_entry(username or "")
        save_users(users)

    # username আপডেট
    if username and users[uid].get("tg_username") != username:
        users[uid]["tg_username"] = username
        save_users(users)

    # ── ভাষা সিলেক্ট না থাকলে আগে ভাষা বাছাই করতে বলো ──────────────────
    if not users[uid].get("language"):
        send_message(chat_id,
            "🌐 <b>ভাষা নির্বাচন করুন / Select Language</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার পছন্দের ভাষা বেছে নিন:\n"
            "Choose your preferred language:",
            language_keyboard()
        )
        return users

    lang = get_lang(users, uid)
    status = users[uid].get("status", "new")

    if is_admin and status == "approved":
        send_message(chat_id, ADMIN_PANEL_TEXT)
        return users

    if not is_admin:
        if status == "new":
            markup = {"inline_keyboard": [[{"text": TEXTS[lang]["link_account"], "callback_data": "link_account"}]]}
            send_message(chat_id, TEXTS[lang]["not_registered"], markup)
        elif status == "pending":
            send_message(chat_id, TEXTS[lang]["pending_msg"])
        elif status == "banned":
            send_message(chat_id, TEXTS[lang]["banned_msg"])
        elif status == "approved":
            send_message(chat_id, TEXTS[lang]["welcome_back"].format(username=username or uid))
        return users

    # Admin, not yet approved
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


def handle_sms_start(chat_id, user_id, users):
    uid = str(user_id)
    is_admin = uid == str(ADMIN_ID)

    if uid not in users or users[uid].get("status") != "approved":
        get_user_guard(uid, users, chat_id)
        return users

    user_workflow = users[uid].get("sms_workflow", "")
    if not user_workflow:
        lang = get_lang(users, uid)
        extra = "নিজে /setwf দিয়ে সেট করুন।" if is_admin else "Admin কে জানান। তিনি সেট করবেন।"
        send_message(chat_id, TEXTS[lang]["no_workflow"] + "\n" + extra)
        return users

    gh_status, _ = get_workflow_status(user_workflow)
    if gh_status in ("in_progress", "queued"):
        send_message(chat_id, t(users, uid, "sms_already_on"))
        return users

    if users[uid].get("sms_on") and gh_status not in ("in_progress", "queued"):
        users[uid]["sms_on"] = False

    send_message(chat_id, t(users, uid, "sms_starting"))

    if trigger_workflow(user_workflow):
        users[uid]["sms_on"] = True
        users[uid]["sms_start_time"] = datetime.utcnow().isoformat()
        save_users(users)
    else:
        send_message(chat_id, t(users, uid, "sms_start_failed"))
    return users


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
        send_message(chat_id, t(users, uid, "sms_not_running"))
        return users

    if cancel_workflow_run(run_id):
        users[uid]["sms_on"] = False
        users[uid]["sms_start_time"] = ""
        save_users(users)
        send_message(chat_id, t(users, uid, "sms_stopped"))
    else:
        send_message(chat_id, t(users, uid, "sms_stop_failed"))
    return users


def handle_status(chat_id, user_id, users):
    uid = str(user_id)

    if uid not in users or users[uid].get("status") != "approved":
        get_user_guard(uid, users, chat_id)
        return users

    lang = get_lang(users, uid)
    txt = TEXTS[lang]
    user_workflow = users[uid].get("sms_workflow", SMS_WORKFLOW)
    gh_status, _ = get_workflow_status(user_workflow)

    if gh_status in ("in_progress", "queued"):
        sms_info = txt["status_on"]
        if not users[uid].get("sms_on"):
            users[uid]["sms_on"] = True
            save_users(users)
    elif gh_status == "completed":
        sms_info = txt["status_off"]
        if users[uid].get("sms_on"):
            users[uid]["sms_on"] = False
            users[uid]["sms_start_time"] = ""
            save_users(users)
    else:
        sms_info = txt["status_unknown"]

    remaining_str = ""
    if gh_status in ("in_progress", "queued"):
        start_time_str = users[uid].get("sms_start_time", "")
        if start_time_str:
            try:
                start_dt = datetime.fromisoformat(start_time_str)
                elapsed = (datetime.utcnow() - start_dt).total_seconds()
                worker_runtime = 195 * 60
                remaining = max(0, int(worker_runtime - elapsed))
                remaining_str = f"\n{txt['remaining']}: {seconds_to_hms(remaining, lang)}"
            except:
                pass

    send_message(chat_id,
        f"{txt['status_title']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{txt['sms_checker']}: {sms_info}{remaining_str}\n"
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
            user_lang = u.get("language", "bn") or "bn"

            text = (
                f"🔍 <b>ইউজার তথ্য</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 Telegram: @{u.get('tg_username', 'N/A')}\n"
                f"🆔 ID: <code>{uid}</code>\n"
                f"🌐 ভাষা: {'বাংলা 🇧🇩' if user_lang == 'bn' else 'English 🇬🇧'}\n"
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

    # ── ভাষা সিলেক্ট callback ─────────────────────────────────────────────
    if data.startswith("set_lang|"):
        lang_choice = data.split("|")[1]
        uid = from_id
        if uid not in users:
            username = callback["from"].get("username", str(from_id))
            users[uid] = make_new_user_entry(username)
        users[uid]["language"] = lang_choice
        save_users(users)
        save_lang_store(users)  # language আলাদা file এ পার্মানেন্ট সেভ
        answer_callback(cb_id, "✅")
        send_message(chat_id, TEXTS[lang_choice]["language_set"])

        # ভাষা সিলেক্টের পরে স্টার্ট প্রক্রিয়া চালিয়ে যাও
        username = callback["from"].get("username", str(from_id))
        users = handle_start(chat_id, int(from_id), username, users)
        return users

    if data == "link_account":
        answer_callback(cb_id)
        uid = from_id
        if uid not in users:
            username = callback["from"].get("username", str(from_id))
            users[uid] = make_new_user_entry(username)
        users[uid]["step"] = "await_username"
        save_users(users)
        lang = get_lang(users, uid)
        send_message(chat_id, TEXTS[lang]["enter_username"])
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

    target_lang = get_lang(users, target_id)

    if action == "approve":
        users[target_id]["status"] = "approved"
        save_users(users)
        answer_callback(cb_id, "✅ Approved!")
        send_message(int(target_id), TEXTS[target_lang]["approved_notice"])
    elif action == "ban":
        users[target_id]["status"] = "banned"
        save_users(users)
        answer_callback(cb_id, "🚫 Banned!")
        send_message(int(target_id), TEXTS[target_lang]["banned_notice"])

    return users

# ── Step Handler ──────────────────────────────────────────────────────────────
def handle_step(chat_id, user_id, text, users):
    uid = str(user_id)
    is_admin = uid == str(ADMIN_ID)

    if uid not in users:
        return users

    step = users[uid].get("step", "")
    lang = get_lang(users, uid)

    if step == "await_username":
        users[uid]["_temp_lamix_username"] = text.strip()
        users[uid]["step"] = "await_password"
        save_users(users)
        send_message(chat_id, TEXTS[lang]["enter_password"])

    elif step == "await_password":
        lamix_username = users[uid].pop("_temp_lamix_username", "")
        lamix_password = text.strip()

        users[uid]["step"] = ""
        save_users(users)

        send_message(chat_id, TEXTS[lang]["verifying"])

        triggered = trigger_workflow(VERIFY_WORKFLOW, {
            "user_id": uid,
            "lamix_username": lamix_username,
            "lamix_password": lamix_password
        })

        if not triggered:
            send_message(chat_id, TEXTS[lang]["verify_failed_trigger"])
            users[uid]["status"] = "new"
            users[uid]["step"] = ""
            save_users(users)

    return users


def handle_verify_result(user_id, success, lamix_username, lamix_password, users):
    uid = str(user_id)
    if uid not in users:
        return users

    tg_username = users[uid].get("tg_username", "")
    lang = get_lang(users, uid)

    if success:
        users[uid]["status"] = "pending"
        users[uid]["verify_status"] = "done"
        users[uid]["step"] = ""
        save_users(users)
        send_message(int(uid), TEXTS[lang]["verify_success"])
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
            send_message(int(uid), TEXTS[lang]["verify_failed"])

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
                target_lang = get_lang(users, uid)
                send_message(int(uid), TEXTS[target_lang]["approved_notice"])
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
                target_lang = get_lang(users, uid)
                send_message(int(uid), TEXTS[target_lang]["banned_notice"])
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
                saved_lang = users[uid].get("language", "bn")
                users[uid]["status"] = "new"
                users[uid]["verify_status"] = ""
                users[uid]["sms_workflow"] = ""
                users[uid]["seen_file"] = ""
                users[uid]["sms_start_time"] = ""
                users[uid]["step"] = ""
                users[uid]["language"] = saved_lang  # ভাষা ধরে রাখো
                save_users(users)
                send_message(chat_id, f"🆕 @{target_username} কে new user করা হয়েছে।")
                target_lang = saved_lang or "bn"
                send_message(int(uid), TEXTS[target_lang]["reset_notice"])
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ @{target_username} পাওয়া যায়নি।")

    elif cmd == "/notice":
        # ── আপডেটেড /notice: নির্দিষ্ট ইউজার বা সবাইকে ────────────────────
        # ফরম্যাট ১: /notice মেসেজ           → সবাইকে
        # ফরম্যাট ২: /notice @username মেসেজ → শুধু ওই ইউজারকে

        rest = text[len("/notice"):].strip()

        if not rest:
            send_message(chat_id,
                "⚠️ ব্যবহার:\n"
                "📢 সবাইকে: /notice আপনার মেসেজ\n"
                "👤 নির্দিষ্ট ইউজারকে: /notice @username মেসেজ"
            )
            return users

        # নির্দিষ্ট ইউজারকে পাঠাতে হবে?
        if rest.startswith("@"):
            rest_parts = rest.split(None, 1)
            target_username = rest_parts[0][1:].lower()  # @ বাদ দিয়ে
            notice_text = rest_parts[1].strip() if len(rest_parts) > 1 else ""

            if not notice_text:
                send_message(chat_id,
                    "⚠️ মেসেজ লিখুন:\n"
                    "/notice @username আপনার মেসেজ"
                )
                return users

            target_id = None
            for uid, u in users.items():
                if u.get("tg_username", "").lower() == target_username:
                    target_id = uid
                    break

            if not target_id:
                send_message(chat_id, f"❌ @{target_username} পাওয়া যায়নি।")
                return users

            try:
                send_message(int(target_id),
                    f"📢 <b>Admin Notice</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"{notice_text}\n"
                    f"━━━━━━━━━━━━━━━"
                )
                send_message(chat_id,
                    f"✅ <b>Notice পাঠানো হয়েছে!</b>\n"
                    f"👤 @{target_username} কে পাঠানো হয়েছে।"
                )
            except Exception as e:
                send_message(chat_id, f"❌ পাঠানো যায়নি: {e}")

        else:
            # সবাইকে broadcast
            notice_text = rest
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
                time.sleep(0.1)

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

    if not users:
        users = collect_old_users(users)

    send_message(ADMIN_ID,
        "✅ <b>Bot চালু হয়েছে!</b>\n"
        "কমান্ড: /users, /approve @username sms-userX.yml, /ban @username\n"
        "📢 /notice <মেসেজ> — সব ইউজারকে broadcast\n"
        "📢 /notice @username <মেসেজ> — নির্দিষ্ট ইউজারকে"
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

            # fresh data লোড
            fresh = load_users()
            for _uid, _u in users.items():
                if _uid in fresh:
                    # in-memory temp field carry করো
                    if "_temp_lamix_username" in _u:
                        fresh[_uid]["_temp_lamix_username"] = _u["_temp_lamix_username"]
                    # language: in-memory তে সেট থাকলে এবং fresh এ খালি হলে preserve করো
                    if _u.get("language") and not fresh[_uid].get("language"):
                        fresh[_uid]["language"] = _u["language"]
            users = fresh

            uid      = str(user_id)
            is_admin = uid == str(ADMIN_ID)

            if uid not in users:
                users[uid] = make_new_user_entry(username or "")
                save_users(users)
            elif username and users[uid].get("tg_username") != username:
                users[uid]["tg_username"] = username
                save_users(users)

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
            elif text == "/language":
                handle_language(chat_id, user_id, users)
            elif text == "/help":
                if is_admin:
                    send_message(chat_id, ADMIN_HELP_TEXT, SUPPORT_MARKUP)
                else:
                    lang = get_lang(users, uid)
                    send_message(chat_id, TEXTS[lang]["help"], SUPPORT_MARKUP)
            else:
                if uid not in users or users[uid].get("status") != "approved":
                    get_user_guard(uid, users, chat_id)
                elif is_admin or users[uid].get("status") == "approved":
                    send_message(chat_id, t(users, uid, "unknown_cmd"))

        time.sleep(2)


if __name__ == "__main__":
    main()
