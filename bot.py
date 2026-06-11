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
RUN_DURATION      = 4 * 60 * 60  # ৪ ঘন্টা

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
    "▶️ /start — SMS চেকার চালু করুন\n"
    "⏹ /stop  — SMS চেকার বন্ধ করুন\n"
    "📊 /status — বর্তমান অবস্থা দেখুন\n"
    "❓ /help  — এই মেনু দেখুন\n"
    "━━━━━━━━━━━━━━━"
)

# ── Users DB ──────────────────────────────────────────────────────────────────
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
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
def notify_admin_new_user(tg_id, tg_username, lamix_username):
    text = (
        f"🆕 <b>নতুন ইউজার রেজিস্ট্রেশন!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 Telegram: @{tg_username}\n"
        f"🆔 ID: <code>{tg_id}</code>\n"
        f"🔑 LAMIX User: <code>{lamix_username}</code>\n"
        f"⏳ Status: Pending\n"
        f"━━━━━━━━━━━━━━━"
    )
    markup = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve|{tg_id}"},
            {"text": "🚫 Ban",     "callback_data": f"ban|{tg_id}"}
        ]]
    }
    send_message(ADMIN_ID, text, markup)

# ── Command Handlers ──────────────────────────────────────────────────────────
def handle_start(chat_id, user_id, username, users):
    uid = str(user_id)

    # Admin
    if uid == str(ADMIN_ID):
        send_message(chat_id,
            "👑 <b>Admin Panel</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "/users — সব ইউজার দেখুন\n"
            "/sms_start — SMS চেকার চালু করুন\n"
            "/sms_stop — SMS চেকার বন্ধ করুন\n"
            "/status — অবস্থা দেখুন"
        )
        return users

    # নতুন ইউজার
    if uid not in users:
        markup = {
            "inline_keyboard": [[
                {"text": "🔗 একাউন্ট যোগ করুন", "callback_data": "link_account"}
            ]]
        }
        send_message(chat_id, WELCOME_TEXT, markup)
        users[uid] = {
            "tg_username": username or "",
            "status": "new",
            "lamix_username": "",
            "sms_on": False,
            "step": ""
        }
        save_users(users)
        return users

    status = users[uid]["status"]

    if status == "new":
        markup = {
            "inline_keyboard": [[
                {"text": "🔗 একাউন্ট যোগ করুন", "callback_data": "link_account"}
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
        send_message(chat_id,
            "⏳ <b>অনুমোদনের অপেক্ষায়</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার একাউন্ট যাচাই হচ্ছে।\n"
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
            "▶️ /start — SMS চেকার চালু\n"
            "⏹ /stop  — SMS চেকার বন্ধ\n"
            "📊 /status — অবস্থা দেখুন\n"
            "━━━━━━━━━━━━━━━"
        )

    return users

def handle_sms_start(chat_id, user_id, users):
    uid = str(user_id)
    is_admin = uid == str(ADMIN_ID)

    if not is_admin and (uid not in users or users[uid]["status"] != "approved"):
        send_message(chat_id, "⚠️ আপনার একাউন্ট approved নয়।")
        return users

    send_message(chat_id, "⏳ SMS চেকার চালু করছি...")
    if trigger_workflow(SMS_WORKFLOW):
        if uid in users:
            users[uid]["sms_on"] = True
            save_users(users)
        send_message(chat_id,
            "✅ <b>SMS চেকার চালু হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "⏱ চলবে: ১৯৫ মিনিট\n"
            "🔄 চেক হবে: প্রতি ১ সেকেন্ডে\n"
            "━━━━━━━━━━━━━━━\n"
            "বন্ধ করতে /stop দিন।"
        )
    else:
        send_message(chat_id, "❌ চালু করা যায়নি। একটু পরে আবার চেষ্টা করুন।")
    return users

def handle_sms_stop(chat_id, user_id, users):
    uid = str(user_id)
    is_admin = uid == str(ADMIN_ID)

    if not is_admin and (uid not in users or users[uid]["status"] != "approved"):
        send_message(chat_id, "⚠️ আপনার একাউন্ট approved নয়।")
        return users

    status, run_id = get_workflow_status(SMS_WORKFLOW)
    if status != "in_progress":
        send_message(chat_id, "⚠️ এখন কোনো SMS চেকার চলছে না।")
        return users

    if cancel_workflow_run(run_id):
        if uid in users:
            users[uid]["sms_on"] = False
            save_users(users)
        send_message(chat_id, "✅ SMS চেকার বন্ধ করা হয়েছে।")
    else:
        send_message(chat_id, "❌ বন্ধ করা যায়নি।")
    return users

def handle_status(chat_id, user_id, users):
    uid = str(user_id)
    status, _ = get_workflow_status(SMS_WORKFLOW)

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
        text += (
            f"{status_icon} @{u.get('tg_username','N/A')}\n"
            f"   LAMIX: {u.get('lamix_username','N/A')} | SMS: {sms_icon}\n"
            f"   ID: <code>{uid}</code>\n\n"
        )
    send_message(chat_id, text)

# ── Callback Handler ──────────────────────────────────────────────────────────
def handle_callback(callback, users):
    data       = callback["data"]
    cb_id      = callback["id"]
    from_id    = str(callback["from"]["id"])
    chat_id    = callback["message"]["chat"]["id"]

    # ইউজার একাউন্ট লিংক শুরু করতে চাইছে
    if data == "link_account":
        answer_callback(cb_id)
        uid = from_id
        if uid in users:
            users[uid]["step"] = "await_username"
            save_users(users)
        send_message(chat_id,
            "🔑 <b>একাউন্ট যোগ করুন</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "আপনার <b>LAMIX Username</b> লিখুন:"
        )
        return users

    # Admin approve/ban
    if from_id != str(ADMIN_ID):
        answer_callback(cb_id, "⚠️ শুধু Admin এই কাজ করতে পারবেন।")
        return users

    action, target_id = data.split("|")

    if target_id not in users:
        answer_callback(cb_id, "ইউজার পাওয়া যায়নি।")
        return users

    if action == "approve":
        users[target_id]["status"] = "approved"
        save_users(users)
        answer_callback(cb_id, "✅ Approved!")
        send_message(target_id,
            "🎉 <b>আপনার একাউন্ট অনুমোদিত হয়েছে!</b>\n"
            "━━━━━━━━━━━━━━━\n"
            "এখন আপনি সব কমান্ড ব্যবহার করতে পারবেন।\n"
            "SMS চেকার চালু করতে /start দিন।"
        )

    elif action == "ban":
        users[target_id]["status"] = "banned"
        save_users(users)
        answer_callback(cb_id, "🚫 Banned!")
        send_message(target_id,
            "🚫 <b>আপনার একাউন্ট ব্যান করা হয়েছে।</b>"
        )

    return users

# ── Step Handler (username/password input) ────────────────────────────────────
def handle_step(chat_id, user_id, text, users):
    uid = str(user_id)
    if uid not in users:
        return users

    step = users[uid].get("step", "")

    if step == "await_username":
        users[uid]["lamix_username"] = text.strip()
        users[uid]["step"] = "await_password"
        save_users(users)
        send_message(chat_id,
            "🔒 এখন আপনার <b>LAMIX Password</b> লিখুন:"
        )

    elif step == "await_password":
        lamix_username = users[uid].get("lamix_username", "")
        lamix_password = text.strip()

        users[uid]["step"] = ""
        users[uid]["status"] = "pending"
        save_users(users)

        send_message(chat_id,
            "⏳ <b>একাউন্ট যাচাই করা হচ্ছে...</b>\n"
            "একটু অপেক্ষা করুন।"
        )

        # Verify workflow trigger করো
        triggered = trigger_workflow(VERIFY_WORKFLOW, {
            "user_id": uid,
            "lamix_username": lamix_username,
            "lamix_password": lamix_password
        })

        if triggered:
            send_message(chat_id,
                "✅ <b>তথ্য পাঠানো হয়েছে!</b>\n"
                "━━━━━━━━━━━━━━━\n"
                "যাচাই হলে Admin অনুমোদন করবেন।\n"
                "অনুমোদন পেলে আপনাকে জানানো হবে।"
            )
            tg_username = users[uid].get("tg_username", "")
            notify_admin_new_user(uid, tg_username, lamix_username)
        else:
            send_message(chat_id,
                "❌ যাচাই করা যায়নি। আবার চেষ্টা করুন।\n"
                "/start দিয়ে শুরু করুন।"
            )
            users[uid]["status"] = "new"
            save_users(users)

    return users

# ── Admin Commands ────────────────────────────────────────────────────────────
def handle_admin_command(chat_id, text, users):
    parts = text.strip().split()
    cmd = parts[0].lower()

    if cmd == "/approve" and len(parts) > 1:
        target_username = parts[1].replace("@", "").lower()
        found = False
        for uid, u in users.items():
            if u.get("tg_username", "").lower() == target_username:
                users[uid]["status"] = "approved"
                save_users(users)
                send_message(chat_id, f"✅ @{target_username} কে approve করা হয়েছে।")
                send_message(uid,
                    "🎉 <b>আপনার একাউন্ট অনুমোদিত হয়েছে!</b>\n"
                    "━━━━━━━━━━━━━━━\n"
                    "SMS চেকার চালু করতে /start দিন।"
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
                send_message(uid, "🚫 <b>আপনার একাউন্ট ব্যান করা হয়েছে।</b>")
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

    return users

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global OFFSET
    start_time = time.time()
    users = load_users()

    send_message(ADMIN_ID,
        "✅ <b>Bot চালু হয়েছে!</b>\n"
        "কমান্ড: /users, /approve @username, /ban @username"
    )

    while True:
        if time.time() - start_time >= RUN_DURATION:
            send_message(ADMIN_ID, "⏰ Bot ৪ ঘন্টা সম্পন্ন। বন্ধ হচ্ছে।")
            break

        updates = get_updates(OFFSET)

        for update in updates:
            OFFSET = update["update_id"] + 1

            # Callback (button press)
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

            uid = str(user_id)
            is_admin = uid == str(ADMIN_ID)

            # Admin commands
            if is_admin and text.startswith("/") and any(
                text.lower().startswith(c) for c in ["/approve", "/ban", "/pending", "/users"]
            ):
                users = handle_admin_command(chat_id, text, users)
                continue

            # Step চলছে কিনা
            if uid in users and users[uid].get("step", "") in ["await_username", "await_password"]:
                if not text.startswith("/"):
                    users = handle_step(chat_id, user_id, text, users)
                    continue

            # Commands
            if text == "/start":
                users = handle_start(chat_id, user_id, username, users)
            elif text == "/sms_start":
                users = handle_sms_start(chat_id, user_id, users)
            elif text == "/stop":
                users = handle_sms_stop(chat_id, user_id, users)
            elif text == "/status":
                users = handle_status(chat_id, user_id, users)
            elif text == "/help":
                if uid == str(ADMIN_ID):
                    send_message(chat_id,
                        "👑 <b>Admin কমান্ড লিস্ট</b>\n"
                        "━━━━━━━━━━━━━━━\n\n"
                        "▶️ /start — SMS চেকার শুরু\n"
                        "⏹ /stop — SMS চেকার বন্ধ\n"
                        "📊 /status — বর্তমান অবস্থা\n"
                        "🔄 /restart — পুনরায় শুরু\n\n"
                        "━━━━━━━━━━━━━━━\n"
                        "👥 /users — সব ইউজার লিস্ট\n"
                        "✅ /approve @username\n"
                        "🚫 /ban @username\n"
                        "⏳ /pending @username\n"
                        "━━━━━━━━━━━━━━━"
                    )
                else:
                    send_message(chat_id, HELP_TEXT)
            elif text == "/sms_start":
                users = handle_sms_start(chat_id, user_id, users)
            elif text == "/sms_stop":
                users = handle_sms_stop(chat_id, user_id, users)
            else:
                if uid in users and users[uid]["status"] == "approved":
                    send_message(chat_id, "⚠️ অপরিচিত কমান্ড। /help দেখুন।")

        time.sleep(2)

if __name__ == "__main__":
    main()
