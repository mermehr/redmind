def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=5,
                           requestsPerConnection=100,
                           pipeline=False
                           )

    # Simple wordlist loop
    for word in open('/usr/share/seclists/Discovery/Web-Content/web-extensions.txt'):
        # Create payload manually or use %s injection
        filename = "shell" + word.strip()
        
        # Construct the request manually here or
        # injecting the payload into the %s marker
        engine.queue(target.req, filename)

def handleResponse(req, interesting):
    
    # Filter
    if req.status != 403 and "Only images are allowed" not in req.response:
        table.add(req)
