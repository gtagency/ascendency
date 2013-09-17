#!/usr/bin/env python

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

class RockPaperScissorsGame(GameBase):
    
    def on_start(self):
        self.send_request_multicast({
            player: {'state':None,'moves':['rock','paper','scissors']}
            for player in self.players
        })

    def on_request_complete(self, replies):
        p1 = self.players[0]
        p2 = self.players[1]

        if replies[p1] not in ['rock', 'paper', 'scissors']:
            self.send_game_over({ p1: 0, p2: 1 })
        if replies[p2] not in ['rock', 'paper', 'scissors']:
            self.send_game_over({ p1: 1, p2: 0 })

        r1 = ['rock', 'paper', 'scissors'].index(replies[p1])
        r2 = ['rock', 'paper', 'scissors'].index(replies[p2])

        score_matrix = [
            [(0.5, 0.5), (0.0, 1.0), (1.0, 0.0)],
            [(1.0, 0.0), (0.5, 0.5), (0.0, 1.0)],
            [(0.0, 0.1), (1.0, 0.0), (0.5, 0.5)]
        ]

        result = score_matrix[r1][r2]
        self.send_game_over({ p1: result[0], p2: result[1] })

    def on_request_timeout(self, replies):
        self.send_request_continue(timeout=0.1)

RockPaperScissorsGame(sys.argv[1], sys.argv[2])
