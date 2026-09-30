"""Behavioral checks against the compiled shell process."""
import pathlib
import subprocess
import unittest
import tempfile
import os

BINARY = pathlib.Path(__file__).resolve().parents[1] / 'build' / 'shell'

def run(commands, cwd=None):
    return subprocess.run([str(BINARY)], input=commands, text=True,
                          capture_output=True, cwd=cwd, timeout=5)

class ShellTests(unittest.TestCase):
    def test_job_numbers_recycle_after_reaping(self):
        result = run('sleep 0.01 &\nsleep 0.1\nsleep 0.01 &\nsleep 0.1\nexit\n')
        self.assertEqual(len(__import__('re').findall(r'\[1\] \d+', result.stdout)), 2)

    def test_reap_multiple_completed_jobs(self):
        result = run('sleep 0.01 &\nsleep 0.02 &\nsleep 0.1\njobs\njobs\nexit\n')
        self.assertEqual(result.stdout.count('Done'), 2)

    def test_completed_job_is_reported_and_removed(self):
        result = run('sleep 0.01 &\nsleep 0.1\njobs\njobs\nexit\n')
        self.assertEqual(result.stdout.count('Done'), 1)
        self.assertNotIn('Running', result.stdout)

    def test_multiple_job_markers(self):
        result = run('sleep 0.2 &\nsleep 0.3 &\njobs\nexit\n')
        self.assertIn('[1]-  Running', result.stdout)
        self.assertIn('[2]+  Running', result.stdout)

    def test_background_program_keeps_output_stream(self):
        result = run("/usr/bin/printf background-output &\nsleep 0.1\nexit\n")
        self.assertIn('background-output', result.stdout)
        self.assertRegex(result.stdout, r'\[1\] \d+')

    def test_append_errors_and_restore_descriptors(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = pathlib.Path(directory) / 'errors'
            errors.write_text('existing\n')
            result = run(f'ls /missing-shell-test 2>> {errors}\necho restored\nexit\n')
            self.assertTrue(errors.read_text().startswith('existing\n'))
            self.assertIn('missing-shell-test', errors.read_text())
            self.assertIn('restored\n', result.stdout)
            self.assertEqual(result.stderr, '')

    def test_quoted_executable_path(self):
        with tempfile.TemporaryDirectory() as directory:
            exe = pathlib.Path(directory) / 'quoted program'
            exe.write_text('#!/bin/sh\nprintf "%s\\n" "$1"\n')
            exe.chmod(0o755)
            result = run(f"'{exe}' 'hello world'\nexit\n")
            self.assertIn('hello world\n', result.stdout)

    def test_single_quotes_preserve_backslashes(self):
        result = run("echo 'hello\\world'\nexit\n")
        self.assertIn("hello\\world\n", result.stdout)

    def test_relative_directory_changes(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        result = run('cd tests\npwd\ncd ..\npwd\nexit\n', root)
        self.assertIn(str(root / 'tests'), result.stdout)
        self.assertIn('$ ' + str(root) + '\n', result.stdout)
        self.assertEqual(result.stderr, '')

if __name__ == '__main__':
    unittest.main()
