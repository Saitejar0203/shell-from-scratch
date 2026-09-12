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

    def test_missing_variable_reports_error(self):
        result = self.shell('declare -p missing\nexit\n')
        self.assertEqual(result.stderr, 'declare: missing: not found\n')

    def test_declare_stores_updates_and_preserves_equals(self):
        result = self.shell('declare foo=bar\ndeclare -p foo\ndeclare foo=a=b\ndeclare -p foo\nexit\n')
        self.assertIn('declare -- foo="bar"\n', result.stdout)
        self.assertIn('declare -- foo="a=b"\n', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_invalid_names_are_not_stored(self):
        result = self.shell('declare 23=x bad-name=y _FOO=bar\ndeclare -p 23 _FOO\nexit\n')
        self.assertIn("declare: `23=x': not a valid identifier\n", result.stderr)
        self.assertIn("declare: `bad-name=y': not a valid identifier\n", result.stderr)
        self.assertIn('declare: 23: not found\n', result.stderr)
        self.assertIn('declare -- _FOO="bar"\n', result.stdout)
