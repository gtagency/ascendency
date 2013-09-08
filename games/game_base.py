
import json
import time
import sys

import requests

class GameBase(object):

    def __init__(self, url, key):
        self.url = url
        self.key = key

        self.send_message('join_as_game')
        join_info = self.recv_message()
        self.config = join_info['config']
        self.players = join_info['players']

        self.on_start()

        while True:
            try:
                event = self.recv_message()
                if event['event'] == 'request_complete':
                    self.on_request_complete(event['replies'])
                elif event['event'] == 'request_timeout':
                    self.on_request_timeout(event['replies'])
            except ValueError as e:
                self.on_error(int(str(e)))

    def send_request_multicast(self, messages, timeout=1.0):
        self.send_message('request', timeout=timeout, messages=messages)

    def send_request(self, player, message, timeout=1.0):
        self.send_request_multicast(timeout=timeout, messages={player:message})

    def send_request_continue(self, timeout=1.0):
        self.send_message('continue', timeout=timeout)

    def send_game_over(self, results):
        self.send_message('game_over', results=results)

    def log(self, data):
        sys.stderr.write(json.dumps(data))
        sys.stderr.write('\n')

    def on_start(self):
        pass

    def on_request_complete(self, replies):
        pass

    def on_resquest_timeout(self, replies):
        pass

    def on_error(self, status):
        pass

    def send_message(self, request, **kw):
        kw['request'] = request
        kw['key'] = self.key
        self._response = requests.post(self.url, data=json.dumps(kw), 
            headers={'content-type':'application/json'})

    def recv_message(self):
        try:
            sys.stderr.write(self._response.text)
            return self._response.json()
        except ValueError:
            raise ValueError, '%d' % self._response.status_code
