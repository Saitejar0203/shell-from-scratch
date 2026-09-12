"""Programmable completion registration and terminal behavior."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
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

    def expect(self, exchange, expected, keys=b""):
        output = exchange(keys)
        deadline = time.monotonic() + 5
        while expected not in output and time.monotonic() < deadline:
            output += exchange()
        self.assertIn(expected, output)
        return output

    def make_script(self, folder, body):
        script = Path(folder, 'completer')
        script.write_text('#!' + sys.executable + '\n' + body + '\n')
        script.chmod(0o755)
        return script

    def test_single_script_candidate_completes_with_space(self):
        with tempfile.TemporaryDirectory() as folder:
            script = self.make_script(folder, 'print("run")')
            with interactive_shell(folder) as exchange:
                exchange()
                exchange(f'complete -C {script} echo\r'.encode())
                self.expect(exchange, b'run ', b'echo \t')
                self.assertIn(b'run next\r\n', exchange(b'next\r'))
