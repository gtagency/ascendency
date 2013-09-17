#!/usr/bin/env python

import random
import json
import time
import sys

import requests

match_url = sys.argv[1]
key = sys.argv[2]

def send_message(message):
    global _event
    _event = requests.post(
        match_url,
        data=json.dumps({'key':key, 'message':message}),
        headers={'content-type':'application/json'}).json()

def recv_message():
    return _event

send_message({'join':True})

while True:
    msg = recv_message()
    if 'moves' in msg:
        time.sleep(2)
        moves = msg['moves']
        move = moves[random.randint(0, len(moves)-1)]
        send_message({'move':move})
