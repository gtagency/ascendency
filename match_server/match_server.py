
import datetime
import socket
import random
import base64
import json
import time
import sys
import os

import tornado.httpclient
import tornado.websocket
import tornado.testing
import tornado.ioloop
import tornado.gen
import tornado.web

ioloop = tornado.ioloop.IOLoop.instance()

import sandbox

#
# Logging facilities
#

class LogMailbox(object):

    def __init__(self):
        self.logs = []
        self.callback = None

    def send(self, message):
        if self.callback is not None:
            callback, self.callback = self.callback, None
            ioloop.add_callback(callback, message)
        else:
            self.logs.append(message)

    def fetch(self, callback):
        if len(self.logs) == 0:
            self.callback = callback
        else:
            logs, self.logs = self.logs, []
            for log in logs:
                ioloop.add_callback(callback, log)

_log_mailbox = LogMailbox()

def _log(event, *rest, **kwargs):
    timestamp = kwargs.pop('timestamp', None)
    if timestamp is None:
        timestamp = datetime.datetime.now().isoformat()
    else:
        timestamp = timestamp.isoformat()
    _log_mailbox.send([event, timestamp] + list(rest))

def log_init(timestamp=None, memory=1024, diskspace=1048576):
    print 'match server starting advertising %d MB RAM, %d MB diskspace' % (memory, diskspace)
    _log('INI', memory, diskspace, timestamp=None)

def log_config(workers, timestamp=None):
    _log('CFG', {'workers':workers}, timestamp=timestamp)

def log_new_match(match_id, game_key, player_keys, game_config, timestamp=None):
    _log('NEW', match_id, game_key, player_keys, game_config, timestamp=timestamp)

def log_send(match_id, key, data, timestamp=None):
    _log('<--', match_id, key, data, timestamp=timestamp)

def log_recv(match_id, key, data, timestamp=None):
    _log('-->', match_id, key, data, timestamp=timestamp)

def log_end_match(match_id, results, timestamp=None):
    _log('END', match_id, results, timestamp=timestamp)

def log_finish(timestamp=None):
    _log('FIN', timestamp=None)

#
# Currently-active matches
#

matches = {}

#
# Error types
#

class AuthError(BaseException):
    pass

class MultipleRequest(BaseException):
    pass

class InvalidRequest(BaseException):
    pass

#
# Mailboxes for message passing
#

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
                ioloop.remove_timeout(self.timeout)
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
                self.timeout = ioloop.add_timeout(
                    datetime.timedelta(seconds=timeout), self._timeout)

    def refresh_timeout(self, callback, timeout=None):
        if self.callback is not None:
            raise MultipleRequest
        if self.replies is None:
            raise InvalidRequest
        if self.timeout is not None:
            ioloop.remove_timeout(self.timeout)
            self.timeout = None
        self.callback = callback
        if timeout is not None:
            self.timeout = ioloop.add_timeout(
                datetime.timedelta(seconds=timeout), self._timeout)

    def _timeout(self):
        self.timeout = None
        callback, self.callback = self.callback, None
        replies = dict(self.replies)
        replies['$timed_out'] = True
        callback(replies)
    
#
# Object representing an active match
#

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

        log_new_match(match_id, game_key, player_keys, game_config)

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
                log_end_match(self.match_id, results)
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

#
# Tornado handler for match messages
#

class MatchHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def post(self, match_id):
        timestamp = datetime.datetime.now()

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

        log_recv(self._used_match_id, self._used_key, request, timestamp=timestamp)

    def on_response(self, data):
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(data))
        self.finish()
        log_send(self._used_match_id, self._used_key, data)

def random_bytes(count):
    return os.urandom(count)

def generate_key():
    return base64.urlsafe_b64encode(random_bytes(9))

def generate_match_id():
    return base64.urlsafe_b64encode(random_bytes(6))

def create_match(match_id, game_filename, game_key, agent_filenames, agent_keys, game_config={}):
    print 'create match ' + game_filename + ' ' + ' '.join(agent_filenames)
    sandboxes = {}
    agent_keys = []
    match_url = 'http://localhost:%d/%s' % (bound_port, match_id)
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
        generate_match_id(),
        '../games/rock_paper_scissors.py',
        generate_key(),
        ['../agents/rock_paper_scissors.py'] * 2,
        [ generate_key(), generate_key() ]
    )

def _scheduler_handler(future):
    connection = future.result()

    def log_loop(message):
        connection.write_message(json.dumps(message))
        _log_mailbox.fetch(callback=log_loop)
    _log_mailbox.fetch(callback=log_loop)

    def pull_loop(future):
        message = future.result()
        if message is None:
            sys.stderr.write('scheduler connection terminated\n')
            sys.exit()

        message = json.loads(message)
        if '$configure' in message:
            print 'reconfiguring:'
            for key in message['$configure']:
                log_config(message['$configure']['workers'])
                print '\t%s : %s' % (json.dumps(key), json.dumps(message['$configure'][key]))
        if '$schedule' in message:
            print 'scheduling match %s' % json.dumps(message['$schedule'])

            init = message['$schedule']
            create_match(
                init['match_id'],
                '../games/%s.py' % init['game'],
                generate_key(),
                [ '../agents/%s/%s.py' % (init['game'], player) for player in init['players'] ],
                [ generate_key() for player in init['players'] ]
            )

        connection.read_message(callback=pull_loop)
    connection.read_message(callback=pull_loop)

    log_init()

def _connect_to_scheduler():
    scheduler_url = sys.argv[1] if len(sys.argv) == 2 else 'ws://localhost:4200/match_server'
    tornado.websocket.websocket_connect(scheduler_url, callback=_scheduler_handler)

bound_port = None

if __name__ == '__main__':
    sock, bound_port = tornado.testing.bind_unused_port()
    ioloop.add_callback(_connect_to_scheduler)
    app = tornado.web.Application(routes)
    server = tornado.httpserver.HTTPServer(app, io_loop=ioloop)
    server.add_sockets([sock])
    server.start()
    ioloop.start()
