**`downloader_template.py` (GET/POST & Files)**

When you need to iterate through IDs (1-100) and download files, even if the filename is hidden by the server (like `download.php`).


- Iterates through a range.
- Handles both GET and POST.
- Auto-detects filenames from headers.
- Has a dedicated "Payload Processor" section if you need to hash the ID.

---

**`idor_template.py` (IDOR / PUT)**

For JSON APIs where you need to:

1. **GET** a user profile.
2. **Edit** a specific field (like email).
3. **PUT** it back to update the server.

This uses Python's `json` library, which is much safer than `sed` or regex because it won't break on quotes.

---

**`encoder.py` (Quick Encode/Decode)**

Check what a hash is, or encode a string for a URL, without writing a full script.