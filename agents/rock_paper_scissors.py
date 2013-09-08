#!/usr/bin/env python

import random
import json
import time
import sys

import requests

match_url = sys.argv[1]
key = sys.argv[2]

def send_message(request, **kw):
    kw['request'] = request
    kw['key'] = key
    global _event
    _event = requests.post(
        match_url, 
        data=json.dumps(kw), 
        headers={'content-type':'application/json'}).json()

def recv_message():
    return _event

send_message('join')
time.sleep(0.95)
send_message('reply', message=['rock', 'paper', 'scissors'][random.randint(0, 2)])
