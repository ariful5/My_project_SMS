import requests
import json
import os
from datetime import datetime, date

# ── Config ───────────────────────────────────────────────────────────────────
BASE_URL     = os.environ["LAMIX_URL"]
USERNAME     = os.environ["LAMIX_USERNAME"]
PASSWORD     = os.environ["LAMIX_PASSWORD"]
TG_TOKEN     = os.environ["TELEGRAM_TOKEN"]
TG_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE    = "seen_ids.json"

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    # Login
    resp = session.get(f"{BASE_URL}/login", timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Solve captcha
    text = soup.get_text(" ", strip=True)
    match = re.search(r'(\d+)\s*([+\-])\s*(\d+)', text)
    captcha = str(int(match.group(1)) + int(match.group(3))) if match and '+' in match.group(2) else "0"

    resp = session.post(f"{BASE_URL}/signin", data={
        "username": USERNAME, 
        "password": PASSWORD, 
        "capt": captcha
    }, timeout=15, allow_redirects=True)

    print("✅ Login OK!")

    # AJAX Request
    today = date.today().strftime("%Y-%m-%d")
    ajax_url = f"{BASE_URL}/client/res/data_smscdr.php"

    params = {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
        "frange": "", "fnum": "", "fcli": "",
        "fgdate": "", "fgmonth": "", "fgrange": "", "fgnumber": "", "fgcli": "",
        "fg": "0", "sEcho": "1", "iColumns": "7", "sColumns": ",,,,,,",
        "iDisplayStart": "0", "iDisplayLength": "25",
        "mDataProp_0": "0", "mDataProp_1": "1", "mDataProp_2": "2",
        "mDataProp_3": "3", "mDataProp_4": "4", "mDataProp_5": "5", "mDataProp_6": "6",
        "sSearch": "", "bRegex": "false", "iSortCol_0": "0", "sSortDir_0": "desc",
        "iSortingCols": "1", "_": str(int(datetime.now().timestamp() * 1000))
    }

    session.headers.update({
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/client/SMSCDRStats",
        "Origin": BASE_URL,
    })

    r = session.get(ajax_url, params=params, timeout=20)

    if r.status_code == 200:
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
        
        print(f"✅ {len(seen)} SMS marked as seen successfully!")
    else:
        print(f"❌ Error: {r.status_code}")

if __name__ == "__main__":
    from bs4 import BeautifulSoup   # Import here
    import re
    main()
