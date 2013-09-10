
import subprocess
import threading
import datetime
import json
import time
import os

import tornado.ioloop

class SandboxedAgent(object):

    def __init__(self, filename, match_id, key):
        self.filename = filename
        self.match_id = match_id
        self.key = key

    def start(self, args=[]):
        self._agent_process = subprocess.Popen(
            [self.filename] + args,
            bufsize=1,
            stdin=open(os.devnull, 'r'),
            stderr=subprocess.PIPE,
            stdout=open(os.devnull, 'w'),
            close_fds=True)
        self._log_thread = threading.Thread(
            target=self.enqueue_output,
            args=(self._agent_process.stderr,))
        self._log_thread.start()

    def enqueue_output(self, out):
        for line in iter(out.readline, b''):
            tornado.ioloop.IOLoop.instance().add_callback(self.log_log, str(datetime.datetime.now()), line)
        out.close()

    def log_log(self, timestamp, line):
        print json.dumps(['LOG', timestamp, self.match_id, self.key, line])

    def teardown(self):
        self._agent_process.kill()
