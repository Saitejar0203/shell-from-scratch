"""History visible to commands, independent of interactive terminal mode."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_path_completion import interactive_shell

ROOT = str(Path(__file__).resolve().parents[1])

class HistoryTests(unittest.TestCase):
    def shell(self, text, folder, **env):
        return subprocess.run([sys.executable, '-m', 'app.main'], input=text,
                              cwd=folder, env={**os.environ, 'HISTFILE': '', 'PYTHONPATH': ROOT, **env},
                              text=True, capture_output=True, timeout=5)

    def test_listing_includes_unknown_and_history_itself(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.shell('echo hello\nmissing_command\nhistory\nexit\n', folder)
            self.assertIn('    1  echo hello\n    2  missing_command\n    3  history\n', result.stdout)

    def test_limit_keeps_original_numbers_and_zero_is_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.shell('echo first\necho second\nhistory 2\nhistory 0\nexit\n', folder)
            self.assertIn('    2  echo second\n    3  history 2\n', result.stdout)
            self.assertNotIn('    1  echo first', result.stdout)
            self.assertNotIn('    4  history 0', result.stdout)

    def test_up_arrow_recalls_older_commands(self):
        with tempfile.TemporaryDirectory() as folder, interactive_shell(folder) as exchange:
            exchange()
            exchange(b'echo first\r')
            exchange(b'echo second\r')
            self.assertIn(b'echo second', exchange(b'\x1b[A'))
            # Readline redraws only the changed suffix on some terminals.
            exchange(b'\x1b[A')
            self.assertIn(b'first\r\n', exchange(b'\r'))

    def test_down_arrow_returns_to_newer_command(self):
        with tempfile.TemporaryDirectory() as folder, interactive_shell(folder) as exchange:
            exchange()
            exchange(b'echo first\r')
            exchange(b'echo second\r')
            exchange(b'\x1b[A\x1b[A')
            exchange(b'\x1b[B')
            self.assertIn(b'second\r\n', exchange(b'\r'))

    def test_recalled_command_executes_and_is_recorded_once(self):
        with tempfile.TemporaryDirectory() as folder, interactive_shell(folder) as exchange:
            exchange()
            exchange(b'echo recalled > result\r')
            Path(folder, 'result').unlink()
            exchange(b'\x1b[A\r')
            self.assertEqual(Path(folder, 'result').read_text(), 'recalled\n')
            output = exchange(b'history\r')
            self.assertIn(b'    1  echo recalled > result', output)
            self.assertIn(b'    2  echo recalled > result', output)
            self.assertIn(b'    3  history', output)

    def test_read_appends_file_entries_after_current_command(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'saved').write_text('echo loaded\n\n')
            result = self.shell('history -r saved\nhistory\nexit\n', folder)
            self.assertIn('    1  history -r saved\n    2  echo loaded\n    3  history\n', result.stdout)
            self.assertEqual(result.stderr, '')

    def test_write_creates_file_and_includes_write_command(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.shell('echo saved\nhistory -w saved\nexit\n', folder)
            self.assertEqual(Path(folder, 'saved').read_text(), 'echo saved\nhistory -w saved\n')
            self.assertEqual(result.stderr, '')
