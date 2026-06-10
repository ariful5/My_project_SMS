import os
import requests
import time

TG_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TG_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
GH_TOKEN    = os.environ["GH_PAT_TOKEN"]
GH_REPO     = os.environ["GH_REPO"]
GH_WORKFLOW = "check-sms.yml"

RUN_DURATION = 4 * 60 * 60  # ৪ ঘন্টা
OFFSET = 0

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
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text}, timeout=10)
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
        return r.status_code == 204
    except:
        return False

def main():
    global OFFSET
    start_time = time.time()

    send_message("🤖 Bot চালু! /start লিখলে SMS চেকার রান হবে।")

    while True:
        elapsed = time.time() - start_time

        # ৪ ঘন্টা শেষ → cleanly exit
        if elapsed >= RUN_DURATION:
            send_message("⏰ Bot ৪ ঘন্টা সম্পন্ন করেছে। বন্ধ হচ্ছে।")
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
                    send_message("✅ SMS চেকার শুরু হয়েছে! ১ ঘন্টা চলবে।")
                else:
                    send_message("❌ Workflow trigger হয়নি। Token চেক করুন।")

            elif text == "/status":
                remaining = int(RUN_DURATION - elapsed)
                send_message(f"ℹ️ Bot সচল। বাকি: {remaining//3600}h {(remaining%3600)//60}m")

        time.sleep(2)

if __name__ == "__main__":
    main()
