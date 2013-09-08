
import json
import time

import tornado.websocket
import tornado.ioloop
import tornado.web

class MatchConfigHandler(tornado.web.RequestHandler):

    def get(self):
        self.write(json.dumps({'foo':'bar'}))

class MatchLogHandler(tornado.websocket.WebSocketHandler):
    
    def open(self, match_server_id, match_id):
        self.match_server_id = match_server_id
        self.match_id = match_id

    def on_message(self, message):
        print self.match_server_id, self.match_id, message

    def on_close(self):
        pass

routes = [
    (r'/match_server/config', MatchConfigHandler),
    (r'/match_server/([-_a-zA-Z0-9]{12})/match_log/([-_a-zA-Z0-9]{12})', MatchLogHandler),
]

if __name__ == '__main__':
     app = tornado.web.Application(routes)
     app.listen(4200)
     tornado.ioloop.IOLoop.instance().start()
