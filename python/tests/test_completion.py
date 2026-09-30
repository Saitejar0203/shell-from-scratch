import os
from contextlib import chdir
from pathlib import Path
import pty
import select
import signal
import sys
import time
import tempfile
import unittest
from unittest.mock import patch

from app.completion import complete_command, matching_commands


class CompletionTests(unittest.TestCase):
    @patch.dict(os.environ, {"PATH": "/nonexistent-completion-test"})
    def test_candidates_and_argument_position(self):
        with patch('app.completion.readline.get_line_buffer', return_value='e'), patch('app.completion.readline.get_begidx', return_value=0):
            self.assertEqual(complete_command('e', 0), 'echo ')
            self.assertEqual(complete_command('e', 1), 'exit ')
            self.assertIsNone(complete_command('e', 2))
            self.assertIsNone(complete_command('unknown', 0))
        with patch('app.completion.readline.get_line_buffer', return_value='echo ech'), patch('app.completion.readline.get_begidx', return_value=5):
            self.assertIsNone(complete_command('ech', 0))

    def test_filename_arguments_use_current_directory_without_command_validation(self):
        with tempfile.TemporaryDirectory() as folder, chdir(folder):
            Path('readme.txt').write_text('file contents')
            Path('readme.txt').chmod(0o644)
            Path('other_directory').mkdir()
            with patch('app.completion.readline.get_begidx', return_value=4):
                for line in ('cat re', 'xyz re'):
                    with patch('app.completion.readline.get_line_buffer', return_value=line):
                        self.assertEqual(complete_command('re', 0), 'readme.txt ')
                        self.assertIsNone(complete_command('re', 1))
                        self.assertIsNone(complete_command('absent', 0))
            Path('another').mkdir()
            with chdir('another'), patch('app.completion.readline.get_begidx', return_value=4), patch('app.completion.readline.get_line_buffer', return_value='cat re'):
                self.assertIsNone(complete_command('re', 0))
                Path('report.txt').write_text('different cwd')
                self.assertEqual(complete_command('re', 0), 'report.txt ')

    def test_path_filters_duplicates_and_refreshes_each_attempt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first, second = root / 'first', root / 'second'
            first.mkdir()
            second.mkdir()
            for directory in (first, second):
                executable = directory / 'custom_executable'
                executable.write_text('#!/bin/sh\necho external-ok\n')
                executable.chmod(0o755)
            (first / 'custom_text').write_text('not executable')
            (first / 'custom_directory').mkdir()
            (first / 'custom_link').symlink_to(first / 'custom_executable')
            path = os.pathsep.join(map(str, [root / 'missing', first / 'custom_text', first, second]))
            with patch.dict(os.environ, {'PATH': path}), patch('app.completion.readline.get_line_buffer', return_value='custom'), patch('app.completion.readline.get_begidx', return_value=0):
                self.assertEqual(complete_command('custom', 0), 'custom_executable ')
                (first / 'custom_link').unlink()
                # Subsequent states use the same snapshot despite file changes.
                self.assertEqual(complete_command('custom', 1), 'custom_link ')
                self.assertIsNone(complete_command('custom', 2))
                self.assertEqual(complete_command('custom', 0), 'custom_executable ')
                self.assertIsNone(complete_command('custom', 1))
            with patch.dict(os.environ, {'PATH': ''}), patch('app.completion.os.scandir', wraps=os.scandir) as scan:
                matching_commands('unlikely_prefix')
                scan.assert_called_once_with('.')

    def test_tab_edits_line_and_completed_commands_execute(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        executable = Path(folder.name) / 'custom_executable'
        executable.write_text('#!/bin/sh\necho external-ok\n')
        executable.chmod(0o755)
        (Path(folder.name) / 'readme.txt').write_text('file-completion-ok\n')
        pid, descriptor = pty.fork()
        if pid == 0:
            os.chdir(Path(__file__).resolve().parents[1])
            os.environ["PATH"] = folder.name + os.pathsep + os.environ.get("PATH", "")
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
            os.write(descriptor, b'custom\t')
            receive(b'custom_executable ')
            os.write(descriptor, b'\r')
            self.assertIn(b'external-ok\r\n', receive(b'$ '))
            os.write(descriptor, ('cd ' + folder.name + '\r').encode())
            receive(b'$ ')
            os.write(descriptor, b'cat re\t')
            receive(b'readme.txt ')
            os.write(descriptor, b'\r')
            self.assertIn(b'file-completion-ok\r\n', receive(b'$ '))
            os.write(descriptor, b'xyz re\t')
            receive(b'readme.txt ')
            os.write(descriptor, b'\r')
            self.assertIn(b'xyz: command not found', receive(b'$ '))
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
