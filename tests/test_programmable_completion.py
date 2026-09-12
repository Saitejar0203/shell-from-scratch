"""Programmable completion registration and terminal behavior."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_path_completion import interactive_shell

ROOT = str(Path(__file__).resolve().parents[1])

class ProgrammableCompletionTests(unittest.TestCase):
    def shell(self, commands):
        return subprocess.run([sys.executable, '-m', 'app.main'], input=commands,
                              env={**os.environ, 'HISTFILE': '', 'PYTHONPATH': ROOT},
                              text=True, capture_output=True, timeout=5)

    def test_complete_is_builtin(self):
        result = self.shell('type complete\nexit\n')
        self.assertIn('complete is a shell builtin\n', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_missing_specification_names_the_command(self):
        result = self.shell('complete -p git\nexit\n')
        self.assertEqual(result.stderr, 'complete: git: no completion specification\n')

    def test_registration_prints_normalized_specification(self):
        result = self.shell("complete   -C '/tmp/a script'   git\ncomplete -p git\ncomplete -C /tmp/replacement git\ncomplete -p git\nexit\n")
        self.assertIn("complete -C '/tmp/a script' git\n", result.stdout)
        self.assertIn("complete -C '/tmp/replacement' git\n", result.stdout)
        self.assertEqual(result.stderr, '')
