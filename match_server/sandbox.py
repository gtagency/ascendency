
import Queue as queue
import subprocess
import threading
import os

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

class SandboxedAgent(object):

    def __init__(self, filename):
        self.filename = filename

    def start(self, args=[]):
        self._agent_process = subprocess.Popen(
            [self.filename] + args,
            bufsize=1,
            stderr=subprocess.PIPE,
            close_fds=True)
        self._log_queue = queue.Queue()
        self._log_thread = threading.Thread(
            target=enqueue_output,
            args=(self._agent_process.stderr, self._log_queue))
        self._log_thread.start()

    def collect_log(self):
        lines = []
        try:
            while True:
                lines.append(self._log_queue.get_nowait())
        except queue.Empty:
            return ''.join(lines)

    def teardown(self):
        self._agent_process.kill()
