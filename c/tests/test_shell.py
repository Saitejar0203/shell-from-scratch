"""Behavioral checks against the compiled shell process."""
import pathlib
import subprocess
import unittest

BINARY = pathlib.Path(__file__).resolve().parents[1] / 'build' / 'shell'

def run(commands, cwd=None):
    return subprocess.run([str(BINARY)], input=commands, text=True,
                          capture_output=True, cwd=cwd, timeout=5)

class ShellTests(unittest.TestCase):
    def test_relative_directory_changes(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        result = run('cd tests\npwd\ncd ..\npwd\nexit\n', root)
        self.assertIn(str(root / 'tests'), result.stdout)
        self.assertIn('$ ' + str(root) + '\n', result.stdout)
        self.assertEqual(result.stderr, '')

if __name__ == '__main__':
    unittest.main()
