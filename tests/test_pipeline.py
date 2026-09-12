"""Pipeline behavior through the shell, with timeouts to catch pipe deadlocks."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = str(Path(__file__).resolve().parents[1])


class PipelineTests(unittest.TestCase):
    def shell(self, text, folder):
        return subprocess.run([sys.executable, '-m', 'app.main'], input=text,
                              cwd=folder, env={**os.environ, 'PYTHONPATH': ROOT},
                              text=True, capture_output=True, timeout=5)

    def test_external_pipeline_and_large_stream(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'data').write_text('hello\n' * 100000)
            result = self.shell('cat data | wc -l\necho "a|b"\nexit\n', folder)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, r'\$\s+100000\n\$ a\|b\n')
            self.assertEqual(result.stderr, '')

    def test_invalid_pipeline_has_no_redirection_side_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.shell('echo hi >out |\nexit\n', folder)
            self.assertIn('expected command after pipe', result.stderr)
            self.assertFalse(Path(folder, 'out').exists())

    def test_builtin_pipeline_and_child_directory_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.shell('echo hello | wc -c\nls | type exit\ncd / | cat\npwd\nexit\n', folder)
            self.assertRegex(result.stdout, r'\$\s+6\n\$ exit is a shell builtin')
            self.assertIn(folder, result.stdout)
            self.assertEqual(result.stderr, '')

    def test_multiple_stages_and_early_consumer_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.shell('echo hello | cat | cat | wc -c\nyes | head -n 3 | wc -l\nexit\n', folder)
            self.assertRegex(result.stdout, r'\$\s+6\n\$\s+3\n')
            self.assertEqual(result.stderr, '')
