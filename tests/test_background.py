"""Check background launch, literal ampersands, and foreground recovery."""

import os
from pathlib import Path
import re
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from app.parser import extract_background, parse_command


class BackgroundTests(unittest.TestCase):
    def test_only_unquoted_trailing_ampersand_starts_background(self):
        for line in ('sleep 30 &', 'sleep 30&'):
            tokens, background = extract_background(parse_command(line))
            self.assertTrue(background)
            self.assertEqual([token[1] for token in tokens], ['sleep', '30'])
        for line in ('echo "&"', "echo '&'", r'echo \&'):
            tokens, background = extract_background(parse_command(line))
            self.assertFalse(background)
            self.assertEqual(tokens[-1][1], '&')
        for line in ('&', 'sleep 30 & echo x', 'sleep 30 &&'):
            with self.assertRaises(ValueError):
                extract_background(parse_command(line))

    def test_prompt_returns_while_jobs_are_alive_and_redirection_is_restored(self):
        root = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as folder:
            shell = subprocess.Popen(
                [sys.executable, '-m', 'app.main'], cwd=folder,
                env={**os.environ, 'PYTHONPATH': root}, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            children = []

            def prompt(command=None):
                if command is not None:
                    shell.stdin.write((command + '\n').encode())
                    shell.stdin.flush()
                data = b''
                deadline = time.monotonic() + 3
                while not data.endswith(b'$ ') and time.monotonic() < deadline:
                    if select.select([shell.stdout], [], [], 0.1)[0]:
                        chunk = os.read(shell.stdout.fileno(), 4096)
                        if not chunk:
                            break
                        data += chunk
                self.assertTrue(data.endswith(b'$ '), repr(data))
                return data

            try:
                prompt()
                self.assertEqual(prompt('jobs'), b'$ ')
                self.assertIn(b'command not found', prompt('nonexistent_background_command &'))
                commands = ('sleep 30 >output.txt &', 'sleep 30&', 'sleep \"30\" &')
                for number, command in enumerate(commands, 1):
                    data = prompt(command)
                    match = re.fullmatch(rb'\[(\d+)\] (\d+)\n\$ ', data)
                    self.assertIsNotNone(match, data)
                    pid = int(match[2])
                    children.append(pid)
                    self.assertEqual(int(match[1]), number)
                    os.kill(pid, 0)  # The advertised PID is still a live process.
                    markers = {1: ['+'], 2: ['-', '+'], 3: [' ', '-', '+']}[number]
                    expected = ''.join(
                        f'[{index}]{marker}  Running                 {text}\n'
                        for index, (marker, text) in enumerate(zip(markers, commands), 1)
                    ).encode()
                    self.assertEqual(prompt('jobs'), expected + b'$ ')
                self.assertEqual(prompt('jobs >listing.txt'), b'$ ')
                self.assertEqual(Path(folder, 'listing.txt').read_bytes(), expected)
                self.assertEqual(Path(folder, 'output.txt').read_text(), '')
                self.assertEqual(prompt('echo responsive'), b'responsive\n$ ')
                self.assertEqual(prompt('echo "&"'), b'&\n$ ')
                start = time.monotonic()
                prompt('sleep 0.2')
                self.assertGreaterEqual(time.monotonic() - start, 0.15)
            finally:
                for pid in children:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                if shell.poll() is None:
                    shell.stdin.write(b'exit\n')
                    shell.stdin.flush()
                    try:
                        shell.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        shell.kill()
                        shell.wait()
                shell.stdin.close()
                shell.stdout.close()


if __name__ == '__main__':
    unittest.main()
