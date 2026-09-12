"""Shell variable behavior through the real command loop."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = str(Path(__file__).resolve().parents[1])

class VariableTests(unittest.TestCase):
    def shell(self, commands, folder=None):
        return subprocess.run([sys.executable, '-m', 'app.main'], input=commands,
                              cwd=folder, env={**os.environ, 'HISTFILE': '', 'PYTHONPATH': ROOT},
                              text=True, capture_output=True, timeout=5)

    def test_declare_is_builtin(self):
        result = self.shell('type declare\nexit\n')
        self.assertIn('declare is a shell builtin\n', result.stdout)
        self.assertEqual(result.stderr, '')
