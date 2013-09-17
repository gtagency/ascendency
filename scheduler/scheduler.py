
import base64
import json
import os

import tornado.websocket
import tornado.ioloop
import tornado.web

ioloop = tornado.ioloop.IOLoop.instance()

match_servers = {}

class Scheduler(object):

    worker_queue = []
    task_queue = []

    @classmethod
    def add_worker(cls, worker):
        if len(cls.task_queue) > 0:
            match = cls.task_queue.pop(0)
            worker.assign_match(match)
        else:
            cls.worker_queue.append(worker)

    @classmethod
    def remove_worker(cls, worker):
        cls.worker_queue.remove(worker)

    @classmethod
    def schedule(cls, match):
        if len(cls.worker_queue) > 0:
            worker = cls.worker_queue.pop(0)
            worker.assign_match(match)
        else:
            cls.task_queue.append(match)

class MatchWorker(object):

    def __init__(self, match_server):
        self.match_server = match_server
        self.busy = False
        self.match = None
        Scheduler.add_worker(self)

    def assign_match(self, match):
        self.match = match
        self.busy = True
        self.match.start(self)
        self.match_server.schedule_match(match, self)

    def free(self):
        if self.busy:
            self.match_server.remove_match(self.match.match_id)
            self.match = None
            self.busy = False
            Scheduler.add_worker(self)

class MatchTask(object):

    index = {}

    @classmethod
    def generate_match_id(cls):
        return base64.urlsafe_b64encode(os.urandom(12))

    def __init__(self, game, players, config):
        match_id = MatchTask.generate_match_id()
        MatchTask.index[match_id] = self
        self.match_id = match_id
        self.game = game
        self.players = players
        self.config = config
        self.state = 'scheduling'
        self.logs = []

    def start(self, worker):
        self.match_server_hostname = worker.match_server.hostname
        self.worker = worker
        self.state = 'starting'

    def log(self, log):
        self.logs.append(log)

    def run(self, match_id, game_key, player_keys, config):
        self.match_id = match_id
        self.game_key = game_key
        self.player_keys = player_keys
        self.state = 'running'

    def finish(self, results):
        self.results = results
        self.state = 'finished'
        self.worker.free()
        self.worker = None
        self.archived = False

    def redo(self):
        self.logs = []
        self.worker.free()
        self.worker = None
        self.state = 'scheduling'

    @property
    def document(self):
        if self.state == 'scheduling':
            return {
                'state' : 'scheduling',
                'game' : self.game,
                'players' : self.players,
                'config' : self.config
            }
        elif self.state == 'starting':
            return {
                'state' : 'starting',
                'game' : self.game,
                'players' : self.players,
                'config' : self.config,
                'match_server': self.match_server_hostname
            }
        elif self.state == 'running':
            return {
                'state' : 'running',
                'game' : self.game,
                'players' : self.players,
                'config' : self.config,
                'match_server': self.match_server_hostname,
                'match_id': self.match_id,
                'game_key': self.game_key,
                'player_keys': self.player_keys,
            }
        elif self.state == 'finished':
            return {
                'state' : 'finished',
                'game' : self.game,
                'players' : self.players,
                'config' : self.config,
                'match_server': self.match_server_hostname,
                'match_id': self.match_id,
                'game_key': self.game_key,
                'player_keys' : self.player_keys,
                'results' : self.results,
                'archived' : self.archived
            }

class MatchServer(object):

    def __init__(self, socket):
        self.socket = socket
        self.hostname = self.socket.request.remote_ip
        self.workers = []
        self.matches = {}
        self.ready = False

    def __lt__(self, other):
        return (self.worker_count - self.free_workers) - (other.worker_count - other.free_workers)

    def send(self, message):
        self.socket.write_message(json.dumps(message))

    def on_message(self, message):
        if message[0] == 'INI':
            self.hostname = self.socket.request.remote_ip
            self.memory = message[2]
            self.diskspace = message[3]
            self.send({'$configure':{'workers':4}})
        elif message[0] == 'CFG':
            for i in range(message[2]['workers']):
                self.workers.append(MatchWorker(self))
            self.ready = True
        elif message[0] == 'FIN':
            self.on_close()
        elif message[2] in MatchTask.index:
            match = MatchTask.index[message[2]]
            if message[0] == 'NEW':
                match.run(*message[2:])
            elif message[0] == 'END':
                match.finish(*message[3:])
            else:
                match.log(message)

    def on_close(self):
        for worker in self.workers:
            worker.busy = False
        for match in self.matches.values():
            match.redo()
        self.matches = {}

    def remove_match(self, match_id):
        if match_id in self.matches:
            del self.matches[match_id]

    def schedule_match(self, match, worker):
        def send_schedule():
            self.send({'$schedule':{
                'match_id': match.match_id,
                'game': match.game,
                'players': match.players,
                'config': match.config
                }})
        ioloop.add_callback(send_schedule)
        self.matches[match.match_id] = match

games = {}
agents = {}

#
# Tornado HTTP server
#

class MatchServerBackendHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        self.match_server = MatchServer(self)
        match_servers[self.request.remote_ip] = self.match_server

    def on_message(self, message):
        message = json.loads(message)
        self.match_server.on_message(message)

    def on_close(self):
        self.match_server.on_close()
        del match_servers[self.match_server.hostname]

class MatchServerIndexHandler(tornado.web.RequestHandler):

    def get(self):
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(list(match_servers.keys())))

class MatchServerHandler(tornado.web.RequestHandler):
    
    def get(self, hostname):
        try:
            server = match_servers[hostname]
        except KeyError:
            raise tornado.web.HTTPError(404)

        self.set_header('content-type', 'application/json')
        self.write(json.dumps({
            'workers' : [
                worker.match.match_id if worker.match else None
                for worker in server.workers
            ],
        }))

class GameIndexHandler(tornado.web.RequestHandler):
    
    def get(self):
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(list(games.keys())))

class GameHandler(tornado.web.RequestHandler):

    def get(self, name):
        try:
            game = games[name]
        except KeyError:
            raise tornado.web.HTTPError(404)

        self.set_header('content-type', 'application/octet-stream')
        self.write(game)

class AgentIndexHandler(tornado.web.RequestHandler):

    def get(self):
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(list(agents.keys())))

class AgentHandler(tornado.web.RequestHandler):
    
    def get(self, name):
        try:
            agent = agents[name]
        except KeyError:
            raise tornado.web.HTTPError(404)

        self.set_header('content-type', 'application/octet-stream')
        self.write(agent)

class MatchIndexHandler(tornado.web.RequestHandler):
    
    def get(self):
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(list(MatchTask.index.keys())))

    def post(self):
        try:
            match_config = json.loads(self.request.body)
            if len(match_config.keys()) != 3:
                raise ValueError
            game = match_config['game']
            players = match_config['players']
            config = match_config['config']
        except ValueError, KeyError:
            raise tornado.web.HTTPError(400)

        match = MatchTask(game, players, config)
        Scheduler.schedule(match)

        self.set_header('content-type', 'application/json')
        self.write(json.dumps(match.match_id))

class MatchHandler(tornado.web.RequestHandler):
    
    def get(self, match_id):
        try:
            match = MatchTask.index[match_id]
        except KeyError:
            raise tornado.web.HTTPError(404)

        self.set_header('content-type', 'application/json')
        self.write(json.dumps(match.document))

    def delete(self, match_id):
        try:
            match = MatchTask.index[match_id]
        except KeyError:
            raise tornado.web.HTTPError(404)
        del MatchTask.index[match_id]

class MatchLogHandler(tornado.web.RequestHandler):
    
    def get(self, match_id):
        try:
            match = MatchTask.index[match_id]
        except KeyError:
            raise tornado.web.HTTPError(400)
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(sorted(match.logs, key=lambda l: l[1])))

routes = [

    # match server backend websocket endpoint
    (r'/match_server', MatchServerBackendHandler),

    # match server health/statistics
    (r'/match_servers/', MatchServerIndexHandler),
    (r'/match_servers/([-_a-zA-Z0-9.]+)', MatchServerHandler),

    # game and agent collections
    (r'/games/', GameIndexHandler),
    (r'/games/([-_a-zA-Z0-9]+)', GameHandler),
    (r'/agents/', AgentIndexHandler),
    (r'/agents/([-_a-zA-Z0-9]+)', AgentHandler),

    # match tracking
    (r'/matches/', MatchIndexHandler),
    (r'/matches/([-_a-zA-Z0-9]+)', MatchHandler),
    (r'/matches/([-_a-zA-Z0-9]+)/logs', MatchLogHandler),
]

if __name__ == '__main__':

    games['rock_paper_scissors'] = ''.join(open('../games/rock_paper_scissors.py'))
    agents['random_choice'] = ''.join(open('../agents/random_choice.py'))

    app = tornado.web.Application(routes)
    app.listen(4200)
    ioloop.start()
