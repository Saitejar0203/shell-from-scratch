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

    def test_empty_script_result_rings_and_does_not_fall_back_to_files(self):
        with tempfile.TemporaryDirectory() as folder:
            script = self.make_script(folder, 'pass')
            Path(folder, 'xyz_file').write_text('')
            with interactive_shell(folder) as exchange:
                exchange()
                exchange(f'complete -C {script} echo\r'.encode())
                self.expect(exchange, b'\x07', b'echo xyz\t')
                self.assertIn(b'xyz\r\n', exchange(b'\r'))

    def test_script_receives_command_current_and_previous_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            script = self.make_script(folder,
                "import sys\nif sys.argv[1:] == ['echo', 'set', 'remote']: print('set-url')\n"
                "elif sys.argv[1:] == ['echo', '', 'echo']: print('first')")
            with interactive_shell(folder) as exchange:
                exchange()
                exchange(f'complete -C {script} echo\r'.encode())
                self.expect(exchange, b'set-url ', b'echo remote set\t')
                exchange(b'\r')
                self.expect(exchange, b'first ', b'echo \t')

    def test_completer_environment_has_full_line_and_byte_cursor(self):
        with tempfile.TemporaryDirectory() as folder:
            script = self.make_script(folder,
                "import os, json\nfrom pathlib import Path\n"
                "Path('context').write_text(json.dumps([os.environ['COMP_LINE'], os.environ['COMP_POINT']]))\n"
                "print('add')")
            with interactive_shell(folder) as exchange:
                exchange()
                exchange(f'complete -C {script} echo\r'.encode())
                self.expect(exchange, b'add ', 'echo α ad\t'.encode())
                import json
                self.assertEqual(json.loads(Path(folder, 'context').read_text()), ['echo α ad', '10'])
                exchange(b'\r')
                # Edit an earlier argument: full line includes text after the cursor.
                self.expect(exchange, b'd  end', b'echo ad end\x1b[D\x1b[D\x1b[D\x1b[D\t')
                self.assertEqual(json.loads(Path(folder, 'context').read_text()), ['echo ad end', '7'])
            self.assertNotIn('COMP_LINE', os.environ)

    def test_multiple_candidates_ring_then_list_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as folder:
            script = self.make_script(folder, "print('push\\nadd\\ncommit')")
            with interactive_shell(folder) as exchange:
                exchange()
                exchange(f'complete -C {script} echo\r'.encode())
                self.expect(exchange, b'\x07', b'echo \t')
                output = self.expect(exchange, b'commit', b'\t')
                self.assertLess(output.index(b'add'), output.index(b'commit'))
                self.assertLess(output.index(b'commit'), output.index(b'push'))
                self.assertIn(b'$ echo ', output)

    def test_first_argument_uses_command_as_previous_word(self):
        with tempfile.TemporaryDirectory() as folder:
            script = self.make_script(folder,
                "import sys\nif sys.argv[1:] == ['echo', 're', 'echo']: print('reset')")
            with interactive_shell(folder) as exchange:
                exchange()
                exchange(f'complete -C {script} echo\r'.encode())
                self.expect(exchange, b'reset ', b'echo re\t')
