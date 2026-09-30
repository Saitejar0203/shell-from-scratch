"""Exercise terminal completion against a real pseudo-terminal."""
import os
import pathlib
import pty
import select
import subprocess
import time
import unittest
BINARY = pathlib.Path(__file__).resolve().parents[1] / 'build' / 'shell'

def interact(keys):
    master, slave = pty.openpty()
    proc = subprocess.Popen([str(BINARY)], stdin=slave, stdout=slave, stderr=slave,
                            env={**os.environ, 'TERM': 'dumb'}, start_new_session=True)
    os.close(slave)
    def read():
        data = b''
        limit = time.monotonic() + .5
        while time.monotonic() < limit:
            if select.select([master], [], [], .05)[0]:
                try: data += os.read(master, 65536)
                except OSError: break
        return data
    data = read()
    for key in keys:
        os.write(master, key)
        data += read()
    proc.terminate(); proc.wait(timeout=3); os.close(master)
    return data

class CompletionTests(unittest.TestCase):
    def test_completed_command_accepts_arguments(self):
        output = interact([b'ech\t', b'hello world\n'])
        self.assertIn(b'hello world\r\n', output)
        self.assertNotIn(b'command not found', output)

if __name__ == '__main__': unittest.main()
