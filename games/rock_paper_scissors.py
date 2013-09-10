#!/usr/bin/env python

import json
import time
import sys

import game_base

class RockPaperScissorsGame(game_base.GameBase):
    
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
