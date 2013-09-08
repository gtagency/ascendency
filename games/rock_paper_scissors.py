#!/usr/bin/env python

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

send_message('join_as_game')

join_info = recv_message()
config = join_info['config']
players = join_info['players']

send_message('request', timeout=1.0, messages={ player: 'pick' for player in players })

reply = recv_message()
if reply['event'] == 'request_complete':
    send_message('game_over', results={ player: 0 for player in players })
elif reply['event'] == 'request_timeout':
    send_message('game_over', results={ player: 0 for player in players })
