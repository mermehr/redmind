#!/usr/bin/env python3

import base64
import hashlib
import urllib.parse
import sys

def process_string(input_str):
    print(f"--- Processing: '{input_str}' ---")
    
    b64 = base64.b64encode(input_str.encode()).decode()
    print(f"[Base64] {b64}")
    
    url_enc = urllib.parse.quote(input_str)
    print(f"https://www.merriam-webster.com/dictionary/enc {url_enc}")
    
    md5 = hashlib.md5(input_str.encode()).hexdigest()
    print(f"[MD5]    {md5}")
    
    chain = hashlib.md5(b64.encode()).hexdigest()
    print(f"[B64>MD5] {chain}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        process_string(sys.argv[1])
    else:
        print("Usage: python3 encoder.py <string>")