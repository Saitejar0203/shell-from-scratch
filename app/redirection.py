"""Manage temporary stdout/stderr destinations and descriptor cleanup."""

from contextlib import ExitStack, contextmanager
import os
import sys


def restore_stream(descriptor, saved_descriptor, stream):
    """Flush redirected output, restore the original destination, and close its copy."""
    try:
        stream.flush()
    finally:
        try:
            os.dup2(saved_descriptor, descriptor)
        finally:
            os.close(saved_descriptor)


@contextmanager
def redirect_streams(destinations):
    """Temporarily apply redirections; yield whether command execution can proceed.

    ExitStack restores saved descriptors even when setup or execution fails.
    """
    streams = {1: sys.stdout, 2: sys.stderr}
    saved_descriptors = set()
    with ExitStack() as cleanup:
        for descriptor, path, mode in destinations:
            stream = streams[descriptor]
            stream.flush()
            if descriptor not in saved_descriptors:
                saved = os.dup(descriptor)
                cleanup.callback(restore_stream, descriptor, saved, stream)
                saved_descriptors.add(descriptor)
            try:
                with open(path, mode) as output_file:
                    os.dup2(output_file.fileno(), descriptor)
            except OSError as error:
                print(f"shell: {path}: {error.strerror}", file=sys.stderr)
                yield False
                return
        yield True
