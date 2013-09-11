
import json
import time
import sys

import requests

class GameBase(object):

    def __init__(self, url, key):
        self.url = url
        self.key = key

        self.send_message({'$activate':True})

        m = self.recv_message()
        self.config, self.players = m['config'], m['players']

        self.on_start()

        while True:
            try:
                msg = self.recv_message()
                if '$timed_out' in msg:
                    del msg['$timed_out']
                    self.on_request_timeout(msg)
                else:
                    self.on_request_complete(msg)
            except ValueError as e:
                self.on_error(int(str(e)))

    def send_request_multicast(self, messages, timeout=1.0):
        self.send_message(messages, timeout=timeout)

    def send_request(self, player, message, timeout=1.0):
        self.send_message({player:message}, timeout=timeout)

    def send_request_continue(self, timeout=1.0):
        self.send_message({'$refresh':True}, timeout=timeout)

    def send_game_over(self, results):
        self.send_message({'$results':results})

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

    def send_message(self, message, timeout=None):
        self._response = requests.post(self.url, 
            data=json.dumps({'key' : self.key, 'message' : message, 'timeout' : timeout}),
            headers={'content-type':'application/json'})

    def recv_message(self):
        try:
            return self._response.json()
        except ValueError:
            raise ValueError, '%d' % self._response.status_code
