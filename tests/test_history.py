"""History visible to commands, independent of interactive terminal mode."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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
