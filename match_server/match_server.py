import base64
import json
import time
import sys
import os

import tornado.httpclient
import tornado.websocket
import tornado.ioloop
import tornado.web

import sandbox

matches = {}

class AuthError(BaseException):
    pass

class StateError(BaseException):
    pass

class Match(object):

    def __init__(self, match_id, game_key, player_keys, game_config, sandboxes):
        self.match_id = match_id
        self.game_key = game_key
        self.player_keys = set(player_keys)
        self.game_config = game_config
        self.sandboxes = sandboxes

        self.join_count = 0
        self.join_target = 1 + len(player_keys)
        
        self.game_callback = None
        self.player_callbacks = { player: None for player in player_keys }
        self.replies = None

    def join_as_game(self, callback, key):
        if key != self.game_key:
            raise AuthError
        self.game_callback = callback
        self.join_count += 1
        if self.join_count == self.join_target:
            self._join_complete()

    def join(self, callback, key):
        if key not in self.player_keys:
            raise AuthError
        self.player_callbacks[key] = callback
        self.join_count += 1
        if self.join_count == self.join_target:
            self._join_complete()

    def _join_complete(self):
        self.game_callback(json.dumps({
            'event' : 'join_complete',
            'players' : list(self.player_keys),
            'config' : self.game_config
        }))

    def request(self, callback, key, timeout, messages):
        if self.replies is not None:
            raise StateError
        if key != self.game_key:
            raise AuthError
        self.game_callback = callback
        for player in messages:
            self.player_callbacks[player](json.dumps(messages[player]))
        self.replies = { player: None for player in messages }
        # TODO timeout

    def reply(self, callback, key, message):
        if self.replies is None:
            raise StateError
        if key not in self.player_keys:
            raise AuthError
        self.player_callbacks[key] = callback
        self.replies[key] = message

        if all(message is not None for message in self.replies.values()):
            self._request_complete()

    def _request_complete(self):
        self.game_callback(json.dumps({
            'event' : 'request_complete',
            'replies' : self.replies,
        }))
        self.replies = None

    def game_over(self, callback, key, results):
        if key != self.game_key:
            raise AuthError
        for sandbox in self.sandboxes.values():
            sandbox.teardown()

    def _collect_logs(self):
        logs = {}
        for key in self.sandboxes:
            logs[key] = self.sandboxes[key].collect_log()
            if len(logs[key]) > 0:
                print '%.5f' % time.time(), 'G' if key == self.game_key else 'P', key, '(stderr)', json.dumps(logs[key])

def generate_key():
    return base64.urlsafe_b64encode(os.urandom(9))

def create_match(match_id, game_filename, agent_filenames, game_config={}):
    sandboxes = {}
    agent_keys = []
    match_url = 'http://localhost:4201/%s' % match_id
    game_key = generate_key()
    game_agent = sandbox.SandboxedAgent(game_filename)
    sandboxes[game_key] = game_agent
    for agent_filename in agent_filenames:
        agent_key = generate_key()
        agent_keys.append(agent_key)
        agent = sandbox.SandboxedAgent(agent_filename)
        sandboxes[agent_key] = agent
    matches[match_id] = Match(match_id, game_key, agent_keys, game_config, sandboxes)
    for key in sandboxes:
        sandboxes[key].start(args=[match_url, key])
    print 'created match %s' % match_id

class MatchHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def post(self, match_id):
        if match_id not in matches:
            raise tornado.web.HTTPError(404)
        match = matches[match_id]

        message = json.loads(self.request.body)
        try:
            request = message['request']
            key = message['key']
            match._collect_logs()
            print '%.5f' % time.time(), 'G' if key == match.game_key else 'P', key, request, self.request.body
            if request == 'request':
                match.request(self.on_response, key, message['timeout'], message['messages'])
            elif request == 'reply':
                match.reply(self.on_response, key, message['message'])
            elif request == 'join':
                match.join(self.on_response, key)
            elif request == 'join_as_game':
                match.join_as_game(self.on_response, key)
            elif request == 'game_over':
                match.game_over(self.on_response, key, message['results'])
            else:
                raise tornado.web.HTTPError(400)
        except KeyError:
            raise tornado.web.HTTPError(400)
        except AuthError:
            raise tornado.web.HTTPError(403)
        except StateError:
            raise tornado.web.HTTPError(400)
 
    def on_response(self, data):
        self.set_header('content-type', 'application/json')
        self.write(data)
        self.finish()

routes = [
    (r'/([-_a-zA-Z0-9]{12})', MatchHandler),
]

if __name__ == '__main__':

    create_match(generate_key(), '../games/rock_paper_scissors.py',
        ['../agents/rock_paper_scissors.py'] * 2
    )

    app = tornado.web.Application(routes)
    app.listen(4201)
    tornado.ioloop.IOLoop.instance().start()
