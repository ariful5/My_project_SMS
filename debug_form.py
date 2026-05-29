import requests
from bs4 import BeautifulSoup

BASE_URL = "http://51.210.208.26/ints"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

resp = session.get(f"{BASE_URL}/login", timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

print("=" * 60)
print("FORM DETAILS:")
for form in soup.find_all("form"):
    print(f"  action='{form.get('action')}' method='{form.get('method')}'")

print("\nALL INPUT FIELDS:")
for inp in soup.find_all("input"):
    print(f"  name='{inp.get('name')}' | type='{inp.get('type')}' | placeholder='{inp.get('placeholder')}' | id='{inp.get('id')}'")

print("\nRAW FORM HTML:")
form = soup.find("form")
if form:
    print(form.prettify()[:2000])
print("=" * 60)
