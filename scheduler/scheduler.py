
import base64
import json
import os

import tornado.websocket
import tornado.ioloop
import tornado.web

ioloop = tornado.ioloop.IOLoop.instance()

match_servers = []

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
        print 'scheduling ' + match.match_id
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
        print 'worker assigned match ' + match.match_id
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

    def __init__(self, match_id, game, players, config):
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

    def run(self, match_id, game_key, player_keys):
        self.match_id = match_id
        self.game_key = game_key
        self.player_keys = player_keys
        self.state = 'running'

    def finish(self, results):
        print '%s finished with %s' % (self.match_id, json.dumps(results))
        self.results = results
        self.state = 'finished'
        self.worker.free()
        self.worker = None

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
                'results' : self.results
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
        elif message[0] == 'END':
            match_id = message[2]
            results = message[3]
            self.matches[match_id].finish(results)
        elif message[0] == 'FIN':
            self.on_close()
        else:
            match_id = message[2]
            if match_id in self.matches:
                self.matches[match_id].log(message)

    def on_close(self):
        for worker in self.workers:
            worker.busy = False
        for match in self.matches.values():
            match.redo()
        self.active_matches = {}

    def remove_match(self, match_id):
        del self.matches[match_id]

    def schedule_match(self, match, worker):
        self.send({'$schedule':{
            'match_id': match.match_id,
            'game': match.game,
            'players': match.players,
            'config': match.config
            }})
        self.matches[match.match_id] = match

#
# Tornado HTTP server
#

class MatchServerHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        self.match_server = MatchServer(self)
        match_servers.append(self.match_server)

    def on_message(self, message):
        message = json.loads(message)
        self.match_server.on_message(message)

    def on_close(self):
        self.match_server.on_close()
        match_servers.remove(self.match_server)

class MatchServerIndexHandler(tornado.web.RequestHandler):

    def get(self):
        self.set_header('content-type', 'application/json')
        self.write(json.dumps({ server.hostname: [worker.busy for worker in server.workers] for server in match_servers}))

class MatchIndexHandler(tornado.web.RequestHandler):
    
    def get(self):
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(list(MatchTask.index.keys())))

class MatchRootHandler(tornado.web.RequestHandler):
    
    def get(self, match_id):
        try:
            match = matches[match_id]
        except KeyError:
            raise tornado.web.HTTPError(400)
        self.write('')

class MatchLogHandler(tornado.web.RequestHandler):
    
    def get(self, match_id):
        try:
            match = matches[match_id]
        except KeyError:
            raise tornado.web.HTTPError(400)
        self.write('')

class MatchLogListener(tornado.websocket.WebSocketHandler):
    
    def open(self):
        pass

    def on_message(self, message):
        pass

    def on_close(self):
        pass

class ScheduleQueueHandler(tornado.web.RequestHandler):
    
    def get(self):
        self.set_header('content-type', 'application/json')
        self.write('[]')

    def post(self):
        print self.request.body
        self.write('')

routes = [
    (r'/match_server', MatchServerHandler),

    (r'/schedule_queue', ScheduleQueueHandler),

    (r'/match_servers/', MatchServerIndexHandler),

    (r'/matches/', MatchIndexHandler),
    (r'/matches/([-_a-zA-Z0-9]+)', MatchRootHandler),
    (r'/matches/([-_a-zA-Z0-9]+)/logs', MatchLogHandler),
    (r'/matches/([-_a-zA-Z0-9]+)/logs', MatchLogListener),
]

def schedule_test():
    if Scheduler.task_queue == []:
        Scheduler.schedule(MatchTask(base64.urlsafe_b64encode(os.urandom(6)), 'rock_paper_scissors', ['a'] * 2, {}))

if __name__ == '__main__':

    tornado.ioloop.PeriodicCallback(schedule_test, 100).start()

    app = tornado.web.Application(routes)
    app.listen(4200)
    ioloop.start()
