#!/usr/bin/env python

import requests

import json
import time
import sys

match_url = sys.argv[1]
key = sys.argv[2]

def send(request, **kw):
    kw['request'] = request
    kw['key'] = key
    global _event = requests.post(
        match_url, 
        data=json.dumps(kw), 
        headers={'content-type':'application/json'}).json()

def recv():
    return _event

send('join')
while True:
    send('reply', message={})
