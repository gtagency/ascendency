#!/usr/bin/env python

import random
import json
import time
import sys

import game_base

class ConnectFourGame(game_base.GameBase):

    def switch_player(self):
        self.current_player ^= 1

    @property
    def valid_moves(self):
        return [ i for i in range(self.config['cols']) if self.board[0][i] is None ]

    def apply_move(self, move):
        if move not in self.valid_moves:
            raise ValueError

    def on_start(self):
        random.shuffle(self.players)
        self.current_player = 0

        self.board = [ [ None ] * self.config['cols'] ] * self.config['rows']
        self.send_reqeust(self.players[self.current_player], { 
            'state' : self.board,
            'moves' : self.valid_moves
        })

    def on_request_complete(self, replies):
        reply = replies[self.players[self.current_player]]

        try:
            self.apply_move(reply)
        except ValueError:
            self.send_game_over({
                self.players[self.current_player]: 0.0,
                self.players[self.current_player ^ 1]: 1.0
            })
        else:
            if self.check_winner():
                self.send_game_over({
                    self.players[self.current_player]: 1.0,
                    self.players[self.current_player ^ 1]: 0.0
                })
            else:
                self.switch_player()
                self.send_request(self.players[self.current_player], {
                    'state' : self.board,
                    'moves' : self.valid_moves
                })
