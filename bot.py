import os
import requests
import time
from datetime import datetime, timezone

TG_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TG_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
GH_TOKEN    = os.environ["GH_PAT_TOKEN"]
GH_REPO     = os.environ["GH_REPO"]
GH_WORKFLOW = "sms-check.yml"

RUN_DURATION = 4 * 60 * 60
OFFSET = 0

HELP_TEXT = (
    "🤖 <b>SMS Alert Bot</b>\n"
    "━━━━━━━━━━━━━━━\n"
    "📋 <b>কমান্ড লিস্ট:</b>\n\n"
    "▶️ /start\n"
    "   SMS চেকার শুরু করবে\n\n"
    "📊 /status\n"
    "   Bot ও SMS চেকারের বাকি সময় দেখাবে\n\n"
    "⛔ /cancel\n"
    "   চলমান SMS চেকার বন্ধ করবে\n\n"
    "❓ /help\n"
    "   এই মেনু দেখাবে\n"
    "━━━━━━━━━━━━━━━"
)

def get_updates(offset):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates"
    try:
        r = requests.get(url, params={"offset": offset, "timeout": 30}, timeout=35)
        return r.json().get("result", [])
    except:
        return []

def send_message(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TG_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
    except:
        pass

def trigger_workflow():
    url = f"https://api.github.com/repos/{GH_REPO}/actions/workflows/{GH_WORKFLOW}/dispatches"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    try:
        r = requests.post(url, json={"ref": "main"}, headers=headers, timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
        return r.status_code == 204
    except Exception as e:
        print(f"Error: {e}")
        return False

def get_sms_status():
    url = f"https://api.github.com/repos/{GH_REPO}/actions/workflows/{GH_WORKFLOW}/runs"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        runs = r.json().get("workflow_runs", [])
        if not runs:
            return "কোনো run পাওয়া যায়নি"
        latest = runs[0]
        status     = latest.get("status", "unknown")
        conclusion = latest.get("conclusion", "")
        created_at = latest.get("created_at", "")
        if status == "in_progress" and created_at:
            started = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            running_sec = int((now_utc - started).total_seconds())
            sms_remaining = max(0, 195 * 60 - running_sec)
            return f"🟢 চলছে | বাকি: {sms_remaining//60}m {sms_remaining%60}s"
        elif status == "completed":
            return f"⚪ শেষ হয়েছে ({conclusion})"
        else:
            return f"🟡 {status}"
    except Exception as e:
        return f"জানা যায়নি ({e})"

def cancel_workflow():
    url = f"https://api.github.com/repos/{GH_REPO}/actions/workflows/{GH_WORKFLOW}/runs"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        runs = r.json().get("workflow_runs", [])
        if not runs:
            return "কোনো run পাওয়া যায়নি"
        latest = runs[0]
        status = latest.get("status", "")
        run_id = latest.get("id", "")
        if status != "in_progress":
            return "⚠️ এখন কোনো run চলছে না"
        cancel_url = f"https://api.github.com/repos/{GH_REPO}/actions/runs/{run_id}/cancel"
        r2 = requests.post(cancel_url, headers=headers, timeout=10)
        if r2.status_code == 202:
            return "✅ SMS চেকার সফলভাবে বন্ধ করা হয়েছে"
        else:
            return f"❌ বন্ধ করা যায়নি ({r2.status_code})"
    except Exception as e:
        return f"Error: {e}"

def main():
    global OFFSET
    start_time = time.time()

    send_message(
        "✅ <b>Bot চালু হয়েছে!</b>\n"
        "━━━━━━━━━━━━━━━\n"
        "কমান্ড দেখতে /help লিখুন।"
    )

    while True:
        elapsed = time.time() - start_time

        if elapsed >= RUN_DURATION:
            send_message(
                "⏰ <b>Bot ৪ ঘন্টা সম্পন্ন করেছে।</b>\n"
                "স্বয়ংক্রিয়ভাবে বন্ধ হচ্ছে।"
            )
            print("✅ ৪ ঘন্টা শেষ। Job Successful।")
            break

        updates = get_updates(OFFSET)
        for update in updates:
            OFFSET = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = str(msg.get("chat", {}).get("id", ""))
            text = msg.get("text", "").strip()

            if chat_id != str(TG_CHAT_ID):
                continue

            if text == "/start":
                send_message("⏳ GitHub Workflow রান করছি...")
                if trigger_workflow():
                    send_message(
                        "✅ <b>SMS চেকার শুরু হয়েছে!</b>\n"
                        "━━━━━━━━━━━━━━━\n"
                        "⏱ চলবে: ১৯৫ মিনিট\n"
                        "🔄 চেক হবে: প্রতি ১ সেকেন্ডে\n"
                        "━━━━━━━━━━━━━━━\n"
                        "বন্ধ করতে /cancel দিন।"
                    )
                else:
                    send_message(
                        "❌ <b>Workflow trigger হয়নি!</b>\n"
                        "━━━━━━━━━━━━━━━\n"
                        "🔍 চেক করুন:\n"
                        "• GH_PAT_TOKEN সঠিক কিনা\n"
                        "• GH_REPO সঠিক কিনা\n"
                        "• Token এ Actions permission আছে কিনা"
                    )

            elif text == "/status":
                remaining_bot = int(RUN_DURATION - elapsed)
                sms_info = get_sms_status()
                send_message(
                    f"📊 <b>Status</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🤖 Bot বাকি: {remaining_bot//3600}h {(remaining_bot%3600)//60}m\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📩 SMS চেকার: {sms_info}\n"
                    f"━━━━━━━━━━━━━━━"
                )

            elif text == "/cancel":
                send_message("⏳ SMS চেকার বন্ধ করছি...")
                result = cancel_workflow()
                send_message(result)

            elif text == "/help":
                send_message(HELP_TEXT)

            else:
                send_message(
                    "⚠️ অপরিচিত কমান্ড!\n"
                    "কমান্ড দেখতে /help লিখুন।"
                )

        time.sleep(2)

if __name__ == "__main__":
    main()
