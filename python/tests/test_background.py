"""Check background launch, literal ampersands, and foreground recovery."""

import os
import io
from contextlib import redirect_stdout
from unittest.mock import Mock, patch
from pathlib import Path
import re
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from app.commands import list_jobs, start_background_job
from app.parser import extract_background, parse_command


class BackgroundTests(unittest.TestCase):
    def test_done_jobs_appear_once_and_markers_shift(self):
        processes = [Mock(), Mock(), Mock()]
        for process in processes:
            process.poll.return_value = None
        jobs = {
            number: {"process": process, "command": f"sleep {number} &"}
            for number, process in enumerate(processes, 1)
        }

        def listing():
            output = io.StringIO()
            with redirect_stdout(output):
                list_jobs(jobs)
            return output.getvalue()

        # Both success (0) and nonzero normal exits count as completed.
        processes[1].poll.return_value = 0
        processes[2].poll.return_value = 7
        self.assertEqual(listing(),
                         "[1]   Running                 sleep 1 &\n"
                         "[2]-  Done                    sleep 2\n"
                         "[3]+  Done                    sleep 3\n")
        self.assertEqual(list(jobs), [1])
        self.assertEqual(listing(), "[1]+  Running                 sleep 1 &\n")
        processes[0].poll.return_value = 0
        self.assertEqual(listing(), "[1]+  Done                    sleep 1\n")
        self.assertEqual(listing(), "")
        for process in processes:
            process.kill.assert_not_called()
            process.wait.assert_not_called()

    def test_prompt_reaping_shows_only_completed_and_recycles_numbers(self):
        running, finished = Mock(), Mock()
        running.poll.return_value = None
        finished.poll.return_value = 0
        jobs = {1: {"process": running, "command": "sleep 30 &"},
                2: {"process": finished, "command": "echo '&' &"}}
        output = io.StringIO()
        with redirect_stdout(output):
            list_jobs(jobs, completed_only=True)
        self.assertEqual(output.getvalue(), "[2]+  Done                    echo '&'\n")
        with patch('app.commands.find_executable', return_value='/bin/sleep'), \
                patch('app.commands.subprocess.Popen') as popen:
            popen.return_value.pid = 123
            self.assertEqual(start_background_job(['sleep', '30'], jobs, 'sleep 30 &')[0], 2)
            popen.return_value.poll.return_value = 0
            running.poll.return_value = 0
            with redirect_stdout(io.StringIO()):
                list_jobs(jobs, completed_only=True)
            self.assertEqual(jobs, {})
            self.assertEqual(start_background_job(['sleep', '30'], jobs, 'sleep 30 &')[0], 1)

    def test_new_job_does_not_overwrite_job_after_removal(self):
        existing = {"process": Mock(), "command": "sleep 30 &"}
        jobs = {1: existing, 3: existing}
        with patch('app.commands.find_executable', return_value='/bin/sleep'), \
                patch('app.commands.subprocess.Popen') as popen:
            popen.return_value.pid = 123
            self.assertEqual(start_background_job(['sleep', '30'], jobs, 'sleep 30 &'),
                             (4, 123))
        self.assertIs(jobs[3], existing)

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
                self.assertRegex(prompt('sleep 0.1 &'), rb'^\[4\] \d+\n\$ ')
                self.assertEqual(prompt('sleep 0.3'),
                                 b'[4]+  Done                    sleep 0.1\n$ ')
                self.assertNotIn(b'Done', prompt('jobs'))
                # Reaping happens after redirect restoration, even on empty input.
                self.assertRegex(prompt('sleep 0.1 &'), rb'^\[4\] \d+\n\$ ')
                time.sleep(0.2)
                self.assertEqual(prompt('echo done >notice.txt'),
                                 b'[4]+  Done                    sleep 0.1\n$ ')
                self.assertEqual(Path(folder, 'notice.txt').read_text(), 'done\n')
                self.assertRegex(prompt('sleep 0.1 &'), rb'^\[4\] \d+\n\$ ')
                time.sleep(0.2)
                self.assertEqual(prompt(''), b'[4]+  Done                    sleep 0.1\n$ ')
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
