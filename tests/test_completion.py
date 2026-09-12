import os
from pathlib import Path
import pty
import select
import signal
import sys
import time
import unittest
from unittest.mock import patch

from app.completion import complete_builtin


class CompletionTests(unittest.TestCase):
    def test_candidates_and_argument_position(self):
        with patch('app.completion.readline.get_line_buffer', return_value='e'), patch('app.completion.readline.get_begidx', return_value=0):
            self.assertEqual(complete_builtin('e', 0), 'echo ')
            self.assertEqual(complete_builtin('e', 1), 'exit ')
            self.assertIsNone(complete_builtin('e', 2))
            self.assertIsNone(complete_builtin('unknown', 0))
        with patch('app.completion.readline.get_line_buffer', return_value='echo ech'), patch('app.completion.readline.get_begidx', return_value=5):
            self.assertIsNone(complete_builtin('ech', 0))

    def test_tab_edits_line_and_completed_commands_execute(self):
        pid, descriptor = pty.fork()
        if pid == 0:
            os.chdir(Path(__file__).resolve().parents[1])
            os.execv(sys.executable, [sys.executable, '-m', 'app.main'])
        reaped = False

        def receive(expected):
            output = b''
            deadline = time.monotonic() + 5
            while expected not in output and time.monotonic() < deadline:
                if select.select([descriptor], [], [], 0.1)[0]:
                    output += os.read(descriptor, 4096)
            self.assertIn(expected, output)
            return output

        try:
            receive(b'$ ')
            os.write(descriptor, b'ech\t')
            receive(b'echo ')
            os.write(descriptor, b'hello\r')
            output = receive(b'$ ')
            self.assertIn(b'hello\r\nhello\r\n', output)
            os.write(descriptor, b'exi\t')
            receive(b'exit ')
            os.write(descriptor, b'\r')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                finished, status = os.waitpid(pid, os.WNOHANG)
                if finished:
                    reaped = True
                    self.assertEqual(os.waitstatus_to_exitcode(status), 0)
                    break
                # Drain terminal output so shutdown can finish flushing it.
                if select.select([descriptor], [], [], 0.02)[0]:
                    try:
                        os.read(descriptor, 4096)
                    except OSError:
                        pass
            self.assertTrue(reaped, 'Completed exit command did not terminate the shell')
        finally:
            if not reaped:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            os.close(descriptor)


if __name__ == '__main__':
    unittest.main()
