import requests
import json
import os
from datetime import datetime, date

# Config
BASE_URL     = os.environ["LAMIX_URL"]
USERNAME     = os.environ["LAMIX_USERNAME"]
PASSWORD     = os.environ["LAMIX_PASSWORD"]
TG_TOKEN     = os.environ["TELEGRAM_TOKEN"]
TG_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE    = "seen_ids.json"

def main():
    # Login + AJAX (আগের কোডের মতো)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    # ... (লগইন + AJAX অংশ আগের মতোই রাখুন)

    # শুধু এই অংশটা নতুন
    today = date.today().strftime("%Y-%m-%d")
    ajax_url = f"{BASE_URL}/client/res/data_smscdr.php"
    params = { ... আগের params ... }   # আগের কোড থেকে কপি করে নিন

    r = session.get(ajax_url, params=params, timeout=20)
    data = r.json()
    rows = data.get("aaData") or data.get("data") or []

    seen = set()
    for row in rows:
        if isinstance(row, dict):
            row = list(row.values())
        row_id = "|".join(str(c) for c in row[:5])
        seen.add(row_id)

    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

    print(f"✅ {len(seen)} SMS marked as seen. Now ready for future notifications!")

if __name__ == "__main__":
    main()
