"""Exercise completion through real terminal input, not just callback returns."""

from contextlib import contextmanager, chdir
import os
from pathlib import Path
import pty
import select
import signal
import sys
import tempfile
import time
import unittest

from app.completion import matching_paths


@contextmanager
def interactive_shell(directory):
    pid, fd = pty.fork()
    if pid == 0:
        os.environ['PYTHONPATH'] = str(Path(__file__).resolve().parents[1])
        os.environ['TERM'] = 'xterm'
        os.chdir(directory)
        os.execv(sys.executable, [sys.executable, '-m', 'app.main'])

    def exchange(keys=b''):
        if keys:
            os.write(fd, keys)
        output = b''
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not select.select([fd], [], [], 0.2 if output else 1)[0]:
                if output:
                    return output
                continue
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            output += chunk
        return output

    try:
        yield exchange
    finally:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        os.close(fd)


class PathCompletionTests(unittest.TestCase):
    def test_nested_absolute_paths_and_missing_directories(self):
        with tempfile.TemporaryDirectory() as folder, chdir(folder):
            Path('path/to').mkdir(parents=True)
            Path('path/to/file.txt').write_text('contents')
            Path('path/to/folder').mkdir()
            self.assertEqual(matching_paths('path/to/fi'), ['path/to/file.txt '])
            self.assertEqual(matching_paths('./path/to/fo'), ['./path/to/folder/'])
            self.assertEqual(matching_paths(folder + '/path/to/fi'), [folder + '/path/to/file.txt '])
            self.assertEqual(matching_paths('missing/f'), [])
            self.assertEqual(matching_paths('path/to/file.txt/f'), [])

    def test_tabs_for_all_remaining_filename_stages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'bar').mkdir()
            (root / 'foo').write_text('root file')
            with interactive_shell(folder) as exchange:
                self.assertIn(b'$ ', exchange())
                # No common prefix: first Tab rings, second lists and redraws.
                self.assertIn(b'\x07', exchange(b'echo \t'))
                listing = exchange(b'\t')
                self.assertIn(b'bar/', listing)
                self.assertIn(b'foo', listing)
                self.assertLess(listing.index(b'bar/'), listing.index(b'foo'))
                self.assertIn(b'$ echo ', listing)
                repeated = exchange(b'\t')
                self.assertIn(b'bar/', repeated)
                self.assertIn(b'foo', repeated)
                self.assertIn(b'$ echo ', repeated)
                # Complete independent arguments and execute to verify the line.
                self.assertIn(b'bar/', exchange(b'b\t'))
                self.assertIn(b'foo ', exchange(b' f\t'))
                self.assertIn(b'\x07', exchange(b'x\t'))
                self.assertIn(b'bar/ foo x\r\n', exchange(b'\r'))
                # A slash is immediately followed by further path completion.
                (root / 'bar' / 'nested').mkdir()
                (root / 'bar' / 'nested' / 'file.txt').write_text('contents')
                self.assertIn(b'bar/', exchange(b'echo b\t'))
                self.assertIn(b'nested/', exchange(b'\t'))
                self.assertIn(b'file.txt ', exchange(b'fi\t'))
                self.assertIn(b'bar/nested/file.txt\r\n', exchange(b'\r'))
                # A missing nested directory must leave the typed path intact.
                self.assertIn(b'\x07', exchange(b'echo missing/z\t'))
                self.assertIn(b'missing/z\r\n', exchange(b'\r'))
                # Progressive shared prefixes must not insert a space or slash early.
                for name in ('xyz_foo', 'xyz_foo_bar', 'xyz_foo_bar_baz'):
                    (root / name).mkdir()
                exchange(b'echo xyz_\t')
                exchange(b'_\t')
                exchange(b'_\t')
                self.assertIn(b'xyz_foo_bar_baz/\r\n', exchange(b'\r'))
                # The same shared-prefix behavior works for non-executable files.
                (root / 'readme.txt').write_text('a')
                (root / 'report.txt').write_text('b')
                exchange(b'echo r\t')
                exchange(b'a\t')
                self.assertIn(b'readme.txt\r\n', exchange(b'\r'))


if __name__ == '__main__':
    unittest.main()
