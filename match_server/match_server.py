
import datetime
import random
import base64
import json
import time
import sys
import os

import tornado.httpclient
import tornado.websocket
import tornado.ioloop
import tornado.gen
import tornado.web

import sandbox

matches = {}

class AuthError(BaseException):
    pass

class MultipleRequest(BaseException):
    pass

class InvalidRequest(BaseException):
    pass

class InitMailbox(object):

    def __init__(self, game, players):
        keys = list(players) + [game]
        self.joins = { key: None for key in keys }
        self.joins_remaining = len(keys)
        self.callback = None

    def send(self, source):
        if source not in self.joins:
            raise InvalidRequest
        if self.joins[source] is not None:
            raise MultipleRequest
        self.joins[source] = True
        self.joins_remaining -= 1
        if self.joins_remaining == 0 and self.callback is not None:
            callback, self.callback = self.callback, None
            callback()

    def fetch(self, callback):
        if self.joins_remaining == 0:
            callback()
        else:
            if self.callback is not None:
                raise MultipleRequest
            self.callback = callback

class PlayerMailbox(object):

    def __init__(self):
        self.queue = []
        self.callback = None

    def send(self, message):
        if self.callback is not None:
            callback, self.callback = self.callback, None
            callback(message)
        else:
            self.queue.append(message)

    def fetch(self, callback):
        if len(self.queue) == 0:
            if self.callback is not None:
                raise MultipleRequest
            self.callback = callback
        else:
            callback(self.queue.pop(0))

class GameMailbox(object):

    def __init__(self):
        self.replies = None
        self.replies_remaining = 0
        self.callback = None
        self.timeout = None
        
    def send(self, source, message):
        if self.replies is None or source not in self.replies:
            raise InvalidRequest
        if self.replies[source] is not None:
            raise MultipleRequest
        self.replies[source] = message
        self.replies_remaining -= 1
        if self.replies_remaining == 0:
            if self.timeout is not None:
                tornado.ioloop.IOLoop.instance().remove_timeout(self.timeout)
                self.timeout = None
            if self.callback is not None:
                callback, self.callback = self.callback, None
                replies, self.replies = self.replies, None
                callback(replies)

    def fetch(self, players, callback, timeout=None):
        if self.callback is not None:
            raise MultipleRequest
        if self.replies is not None:
            replies, self.replies = self.replies, None
            callback(replies)
        else:
            self.replies = { player: None for player in players }
            self.replies_remaining = len(players)
            self.callback = callback
            if timeout is not None:
                self.timeout = tornado.ioloop.IOLoop.instance().add_timeout(
                    datetime.timedelta(seconds=timeout), self._timeout)

    def refresh_timeout(self, callback, timeout=None):
        if self.callback is not None:
            raise MultipleRequest
        if self.replies is None:
            raise InvalidRequest
        if self.timeout is not None:
            tornado.ioloop.IOLoop.instance().remove_timeout(self.timeout)
            self.timeout = None
        self.callback = callback
        if timeout is not None:
            self.timeout = tornado.ioloop.IOLoop.instance().add_timeout(
                datetime.timedelta(seconds=timeout), self._timeout)

    def _timeout(self):
        self.timeout = None
        callback, self.callback = self.callback, None
        replies = dict(self.replies)
        replies['$timed_out'] = True
        callback(replies)

class Match(object):
    
    def __init__(self, match_id, game_key, player_keys, game_config, sandboxes):
        self.match_id = match_id
        self.game = game_key
        self.players = set(player_keys)
        self.game_config = game_config
        self.sandboxes = sandboxes

        self.init_mailbox = InitMailbox(game_key, player_keys)
        self.game_mailbox = GameMailbox()
        self.player_mailbox = { player: PlayerMailbox() for player in self.players }

        print json.dumps(['NEW', str(datetime.datetime.now()), match_id, game_key, player_keys, game_config])

    def dispatch(self, key, message, timeout, callback):
        if key == self.game:
            self.game_dispatch(message, timeout, callback)
        elif key in self.players:
            if timeout is not None:
                raise InvalidRequest
            self.player_dispatch(key, message, callback)
        else:
            raise AuthError

    def game_dispatch(self, message, timeout, callback):
        if message is None:
            self.game_mailbox.fetch(callback)
        elif isinstance(message, dict):
            if '$activate' in message:
                self.init_mailbox.send(self.game)
                self.init_mailbox.fetch(lambda: self._join_complete(callback))
            elif '$results' in message:
                results = message['$results']
                if len(results.keys()) != len(self.players):
                    raise InvalidRequest
                for player in results:
                    if player not in self.players:
                        raise InvalidRequest
                for sandbox in self.sandboxes.values():
                    sandbox.teardown()
                matches[self.match_id] = None
                print json.dumps(['END', str(datetime.datetime.now()), self.match_id, results])
            elif '$refresh' in message:
                self.game_mailbox.refresh_timeout(callback, timeout=timeout)
            else:
                for player in message:
                    if player not in self.players:
                        raise InvalidRequest
                for player in message:
                        self.player_mailbox[player].send(message[player])
                self.game_mailbox.fetch(message.keys(), callback, timeout=timeout)
        else:
            raise InvalidRequest

    def _join_complete(self, callback):
        self.init_mailbox = None
        callback({
            'config' : self.game_config,
            'players' : list(self.players)
        })

    def player_dispatch(self, player, message, callback):
        if message is not None:
            if self.init_mailbox is not None:
                self.init_mailbox.send(player)
            else:
                self.game_mailbox.send(player, message)
        self.player_mailbox[player].fetch(callback)

class MatchHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def post(self, match_id):
        timestamp = str(datetime.datetime.now())

        if match_id not in matches:
            raise tornado.web.HTTPError(404)
        match = matches[match_id]

        try:
            request = json.loads(self.request.body)
            message = request['message']
            key = request['key']
            self._used_key = key
            self._used_match_id = match_id
            if 'timeout' in request:
                timeout = request['timeout']
            else:
                timeout = None
            match.dispatch(key, message, timeout, self.on_response)
        except AuthError:
            raise tornado.web.HTTPError(403)
        except (InvalidRequest, MultipleRequest, KeyError, ValueError):
            raise tornado.web.HTTPError(400)

        print json.dumps(['-->', timestamp, self._used_match_id, self._used_key, request])

    def on_response(self, data):
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(data))
        self.finish()
        print json.dumps(['<--', str(datetime.datetime.now()), self._used_match_id, self._used_key, data])

def generate_key():
    return base64.urlsafe_b64encode(os.urandom(6))

def create_match(match_id, game_filename, agent_filenames, game_config={}):
    sandboxes = {}
    agent_keys = []
    match_url = 'http://localhost:4201/%s' % match_id
    game_key = generate_key()
    game_agent = sandbox.SandboxedAgent(game_filename, match_id, game_key)
    sandboxes[game_key] = game_agent
    for agent_filename in agent_filenames:
        agent_key = generate_key()
        agent_keys.append(agent_key)
        agent = sandbox.SandboxedAgent(agent_filename, match_id, agent_key)
        sandboxes[agent_key] = agent
    matches[match_id] = Match(match_id, game_key, agent_keys, game_config, sandboxes)
    for key in sandboxes:
        sandboxes[key].start(args=[match_url, key])

routes = [
    (r'/([-_a-zA-Z0-9]+)', MatchHandler),
]

def _create_test_matches():

    create_match(
        generate_key(),
        '../games/rock_paper_scissors.py',
        ['../agents/rock_paper_scissors.py'] * 2
    )

if __name__ == '__main__':
    
    print json.dumps(['INI', str(datetime.datetime.now())])

#    tornado.ioloop.IOLoop.instance().add_timeout(0.1, _create_test_matches)

    tester = tornado.ioloop.PeriodicCallback(_create_test_matches, 0.1)
    tester.start()

    app = tornado.web.Application(routes)
    app.listen(4201)
    tornado.ioloop.IOLoop.instance().start()
