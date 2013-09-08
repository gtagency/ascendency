import json
import time

import tornado.ioloop
import tornado.web

matches = {}

class AuthError(BaseException):
    pass

class StateError(BaseException):
    pass

class Match(object):

    def __init__(self, match_id, game_key, player_keys, game_config):
        self.match_id = match_id
        self.game_key = game_key
        self.player_keys = player_keys
        self.game_config = game_config

        self.join_count = 0
        self.join_target = 1 + len(player_keys)
        
        self.game_callback = None
        self.player_callbacks = { player: None for player in player_keys }

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

        if all(message is not None for message in self.collector.values()):
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
        for player in self.player_keys:
            self.player_callbacks[player](json.dumps({'event':'game_over','results':results}))

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
    app = tornado.web.Application(routes)
    app.listen(4200)
    tornado.ioloop.IOLoop.instance().start()
