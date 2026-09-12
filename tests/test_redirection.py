from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'app' / 'main.py'


class RedirectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def run_shell(self, commands):
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=commands + '\nexit\n', text=True, capture_output=True,
            cwd=self.directory, timeout=10,
        )

    def test_builtin_overwrite_and_restore(self):
        (self.directory / 'out').write_text('old contents that must disappear')
        result = self.run_shell('echo hello > out extra\necho world')
        self.assertEqual(result.returncode, 0)
        self.assertEqual((self.directory / 'out').read_text(), 'hello extra\n')
        self.assertEqual(result.stdout, '$ $ world\n$ ')
        self.assertEqual(result.stderr, '')

    def test_operators_without_spaces_and_numeric_arguments(self):
        result = self.run_shell('echo one 1>first\necho two>second\necho 1 >third\necho "1">fourth')
        for name, expected in [('first', 'one\n'), ('second', 'two\n'), ('third', '1\n'), ('fourth', '1\n')]:
            self.assertEqual((self.directory / name).read_text(), expected)
        self.assertEqual(result.stderr, '')

    def test_quoted_operators_and_filenames(self):
        result = self.run_shell(r'''echo '>' \> "1>" > 'file name'
echo hello > '>'
echo foo'>'bar > other''')
        self.assertEqual((self.directory / 'file name').read_text(), '> > 1>\n')
        self.assertEqual((self.directory / '>').read_text(), 'hello\n')
        self.assertEqual((self.directory / 'other').read_text(), 'foo>bar\n')
        self.assertEqual(result.stderr, '')

    def test_external_stdout_and_stderr(self):
        (self.directory / 'source').write_text('data\n')
        result = self.run_shell('cat source missing 1>out\necho after')
        self.assertEqual((self.directory / 'out').read_text(), 'data\n')
        self.assertIn('missing', result.stderr)
        self.assertEqual(result.stdout, '$ $ after\n$ ')

    def test_syntax_errors_do_not_create_files(self):
        result = self.run_shell('echo bad > out >\necho bad > > out\necho after')
        self.assertFalse((self.directory / 'out').exists())
        self.assertEqual(result.stderr.count('expected filename'), 2)
        self.assertEqual(result.stdout, '$ $ $ after\n$ ')

    def test_open_failure_restores_stdout_and_skips_command(self):
        result = self.run_shell('echo bad > first > missing/out\necho after')
        self.assertEqual((self.directory / 'first').read_text(), '')
        self.assertIn('missing/out', result.stderr)
        self.assertEqual(result.stdout, '$ $ after\n$ ')

    def test_multiple_redirections_and_redirection_only(self):
        result = self.run_shell('echo hello > first > second\n> empty')
        self.assertEqual((self.directory / 'first').read_text(), '')
        self.assertEqual((self.directory / 'second').read_text(), 'hello\n')
        self.assertEqual((self.directory / 'empty').read_text(), '')
        self.assertEqual(result.stderr, '')

    def test_cd_stays_in_shell_process(self):
        (self.directory / 'child').mkdir()
        result = self.run_shell('cd child > out\npwd')
        self.assertEqual((self.directory / 'out').read_text(), '')
        self.assertIn(str((self.directory / 'child').resolve()), result.stdout)
        self.assertEqual(result.stderr, '')

    def test_repeated_redirections_and_redirected_exit(self):
        result = self.run_shell(('echo ok > out\n' * 300) + 'exit > last')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, '')
        self.assertEqual((self.directory / 'out').read_text(), 'ok\n')
        self.assertEqual((self.directory / 'last').read_text(), '')

    def test_stderr_redirect_preserves_stdout(self):
        (self.directory / 'source').write_text('data\n')
        result = self.run_shell('cat source missing 2>errors\necho hello 2>empty')
        self.assertIn('missing', (self.directory / 'errors').read_text())
        self.assertEqual((self.directory / 'empty').read_text(), '')
        self.assertEqual(result.stdout, '$ data\n$ hello\n$ ')
        self.assertEqual(result.stderr, '')

    def test_builtin_stderr_overwrite_and_restore(self):
        (self.directory / 'errors').write_text('old diagnostic')
        result = self.run_shell('cd missing 2>errors\ncd other_missing')
        self.assertEqual((self.directory / 'errors').read_text(),
                         'cd: missing: No such file or directory\n')
        self.assertEqual(result.stderr, 'cd: other_missing: No such file or directory\n')

    def test_both_streams_and_partial_setup_failure(self):
        (self.directory / 'source').write_text('data\n')
        result = self.run_shell('cat source missing >out 2>errors\necho skipped 2>first >absent/out\necho after\ncd missing')
        self.assertEqual((self.directory / 'out').read_text(), 'data\n')
        self.assertIn('missing', (self.directory / 'errors').read_text())
        self.assertEqual(result.stdout, '$ $ $ after\n$ $ ')
        self.assertIn('absent/out', (self.directory / 'first').read_text())
        self.assertNotIn('absent/out', result.stderr)
        self.assertIn('cd: missing:', result.stderr)

    def test_quoted_stderr_operator_and_separated_two(self):
        result = self.run_shell(r'''echo '2>' 2\> >literal
echo 2 >number
echo "2">quoted-number''')
        self.assertEqual((self.directory / 'literal').read_text(), '2> 2>\n')
        self.assertEqual((self.directory / 'number').read_text(), '2\n')
        self.assertEqual((self.directory / 'quoted-number').read_text(), '2\n')
        self.assertEqual(result.stderr, '')

    def test_missing_stderr_filename(self):
        result = self.run_shell('echo skipped 2>\necho after')
        self.assertIn('expected filename after 2>', result.stderr)
        self.assertEqual(result.stdout, '$ $ after\n$ ')

    def test_append_stdout_creates_preserves_and_overwrites(self):
        result = self.run_shell('echo first>>out\necho second 1>>out\ncat out\necho replacement >out\necho last >>out\necho visible')
        self.assertEqual((self.directory / 'out').read_text(), 'replacement\nlast\n')
        self.assertEqual(result.stdout, '$ $ $ first\nsecond\n$ $ $ visible\n$ ')
        self.assertEqual(result.stderr, '')

    def test_append_stderr_and_stdout_are_independent(self):
        (self.directory / 'errors').write_text('existing\n')
        (self.directory / 'source').write_text('data\n')
        result = self.run_shell('cat source missing 2>>errors\ncd absent 2>>errors\necho visible 2>>empty\ncd other')
        errors = (self.directory / 'errors').read_text()
        self.assertTrue(errors.startswith('existing\n'))
        self.assertIn('missing', errors)
        self.assertTrue(errors.endswith('cd: absent: No such file or directory\n'))
        self.assertEqual((self.directory / 'empty').read_text(), '')
        self.assertEqual(result.stdout, '$ data\n$ $ visible\n$ $ ')
        self.assertEqual(result.stderr, 'cd: other: No such file or directory\n')

    def test_append_external_output_and_error_together(self):
        (self.directory / 'source').write_text('data\n')
        result = self.run_shell('cat source missing >>out 2>>errors\ncat source missing >>out 2>>errors')
        self.assertEqual((self.directory / 'out').read_text(), 'data\ndata\n')
        self.assertEqual((self.directory / 'errors').read_text().count('missing'), 2)
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout, '$ $ $ ')

    def test_append_quoted_operators_and_missing_destination(self):
        result = self.run_shell(r'''echo '>>' \>\> '2>>' >>'file name'
echo skipped >>
echo skipped 2>>
echo skipped >>>out
echo after''')
        self.assertEqual((self.directory / 'file name').read_text(), '>> >> 2>>\n')
        self.assertEqual(result.stderr.count('expected filename'), 3)
        self.assertFalse((self.directory / 'out').exists())
        self.assertEqual(result.stdout, '$ $ $ $ $ after\n$ ')

    def test_append_failure_preserves_file_and_restores_streams(self):
        (self.directory / 'errors').write_text('existing\n')
        result = self.run_shell('echo skipped 2>>errors >>absent/out\necho after\ncd missing')
        errors = (self.directory / 'errors').read_text()
        self.assertTrue(errors.startswith('existing\n'))
        self.assertIn('absent/out', errors)
        self.assertEqual(result.stdout, '$ $ after\n$ $ ')
        self.assertEqual(result.stderr, 'cd: missing: No such file or directory\n')


if __name__ == '__main__':
    unittest.main()
