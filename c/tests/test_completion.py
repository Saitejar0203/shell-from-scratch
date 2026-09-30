"""Exercise terminal completion against a real pseudo-terminal."""
import os
import pathlib
import pty
import select
import subprocess
import time
import unittest
import tempfile
BINARY = pathlib.Path(__file__).resolve().parents[1] / 'build' / 'shell'

def interact(keys, environment=None):
    master, slave = pty.openpty()
    proc = subprocess.Popen([str(BINARY)], stdin=slave, stdout=slave, stderr=slave,
                            env={**os.environ, 'TERM': 'dumb', **(environment or {})}, start_new_session=True)
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
    def test_missing_file_completion_rings_bell(self):
        with tempfile.TemporaryDirectory() as directory:
            output = interact([f'echo {directory}/missing'.encode() + b'\t'])
            self.assertIn(b'\a', output)

    def test_directory_completion_appends_slash(self):
        with tempfile.TemporaryDirectory() as directory:
            (pathlib.Path(directory) / 'folder').mkdir()
            output = interact([f'echo {directory}/fold'.encode() + b'\t'])
            self.assertIn(b'er/', output)
            self.assertNotIn(b'er/ ', output)

    def test_nested_file_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            nested = pathlib.Path(directory) / 'nested'
            nested.mkdir(); (nested / 'example.txt').touch()
            output = interact([f'echo {nested}/exam'.encode() + b'\t'])
            self.assertIn(b'ple.txt', output)

    def test_completion_extends_only_common_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ['custom_common_one', 'custom_common_two']:
                p = pathlib.Path(directory) / name
                p.write_text('#!/bin/sh\n'); p.chmod(0o755)
            output = interact([b'custom_\t'], {'PATH': directory})
            self.assertIn(b'common_', output)
            self.assertNotIn(b'custom_common_one  ', output)

    def test_ambiguous_commands_are_sorted(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ['custom_zebra', 'custom_apple']:
                p = pathlib.Path(directory) / name
                p.write_text('#!/bin/sh\n'); p.chmod(0o755)
            output = interact([b'custom_\t', b'\t'], {'PATH': directory})
            self.assertIn(b'custom_apple', output)
            self.assertIn(b'custom_zebra', output)

    def test_unknown_prefix_rings_bell(self):
        output = interact([b'nonexistent_unique_shell_prefix\t'])
        self.assertIn(b'\a', output)

    def test_completed_command_accepts_arguments(self):
        output = interact([b'ech\t', b'hello world\n'])
        self.assertIn(b'hello world\r\n', output)
        self.assertNotIn(b'command not found', output)

if __name__ == '__main__': unittest.main()
