
import json

import tornado.websocket
import tornado.ioloop
import tornado.web

ioloop = tornado.ioloop.IOLoop.instance()

match_servers = []

class MatchTracker(object):

    def __init__(self, game, players, config):
        self.game = game
        self.players = players
        self.config = config
        self.state = 'scheduling'
        self.logs = []

    def start(self, match_server_hostname):
        self.match_server_hostname = match_server_hostname
        self.state = 'starting'

    def log(self, log):
        self.logs.append(log)

    def run(self, match_id, game_key, player_keys):
        self.match_id = match_id
        self.game_key = game_key
        self.player_keys = player_keys
        self.state = 'running'

    def finish(self, results):
        self.results = results
        self.state = 'finished'

    def redo(self):
        self.logs = []
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
        self.free_workers = 0
        self.worker_count = 0
        self.active_matches = {}
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
            self.worker_count = message[2]['workers']
            self.free_workers = self.worker_count
            self.ready = True
        elif message[0] == 'END':
            match_id = message[2]
            results = message[3]
            self.active_matches[match_id].finish(results)
            self.free_workers += 1
        elif message[0] == 'FIN':
            self.on_close()
        else:
            match_id = message[2]
            matches[match_id].log(message)

    def on_close(self):
        for match in self.active_matches.values():
            match.redo()
        self.active_matches = {}

    def schedule_match(self, match_id, config):
        self.free_workers -= 1
        self.send({'$schedule':{'match_id':match_id,'config':config}})
        self.active_matches

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
        self.write(json.dumps([server.hostname for server in match_servers]))

class MatchIndexHandler(tornado.web.RequestHandler):
    
    def get(self):
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(list(matches.keys())))

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

def schedule_match(game, players):
    pass

if __name__ == '__main__':
    schedule_match('rock_paper_scissors', ['rock_paper_scissors'] * 2)

    app = tornado.web.Application(routes)
    app.listen(4200)
    ioloop.start()