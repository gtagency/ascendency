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
    return requests.post(
        match_url,
        data=json.dumps(kw),
        headers={'content-type':'application/json'}).json()

join_info = send('join_as_game')
config = join_info['config']
players = join_info['players']

for i in range(10):
    for player in players:
        replies = send('request', timeout=1.0, messages={ player: {} })
        sys.stderr.write(json.dumps(replies))

send('game_over')
