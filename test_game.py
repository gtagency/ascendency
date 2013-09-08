#!/usr/bin/env python

import sys
import json
import requests

_last_reply = None

_match_id = ''
_key = None

class GameMatchProxy(object):

    def __init__(self, endpoint, key):
        self.match_id = match_id
        self.server = server
        self.key = key

        reply = self._send_message('join_as_game')
        if reply['event'] != 'join_complete':
            
        self.game_config = self._send_message('join_as_game')['config']

    def _send_message(self, request, **kw):
        kw['key'] = self.key
        kw['request'] = request
        return requests.post(self.endpoint,
                             headers={'content-type':'application/json'},
                             data=json.dumps(kw)).json()

    def get_event(self):
        

def get_event():
    event = _last_reply
    _last_reply = None
    return event

if __name__ == '__main__':

    if len(sys.argv) != 3:
        print 'Usage: %s MATCH_ID GAME_KEY' % sys.argv[0]
        sys.exit()
    match_id = sys.argv[1]
    key = sys.argv[2]

    match = GameMatchProxy(match_id, key, server='http://localhost:4200')

    while True:
        event = match.get_event()
        if event['event'] == 'request_complete':
            
        elif event['event'] == 'request_timeout':
            pass
        else:
            raise Exception
