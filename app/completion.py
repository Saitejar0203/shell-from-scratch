"""Supply command and filename candidates to the line editor."""

import os
import readline

from app.commands import BUILTINS


_matches = []


def matching_commands(prefix):
    """Collect unique command names, skipping unusable PATH directories."""
    names = {name for name in BUILTINS if name.startswith(prefix)}
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        # An empty PATH entry means the current working directory.
        directory = directory or "."
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if (entry.name.startswith(prefix)
                            and entry.is_file()
                            and os.access(entry.path, os.X_OK)):
                        names.add(entry.name)
        except OSError:
            continue
    return sorted(names)


def matching_files(prefix):
    """Find file arguments in the current directory; executability is irrelevant."""
    try:
        with os.scandir(".") as entries:
            return sorted(entry.name for entry in entries
                          if entry.name.startswith(prefix) and entry.is_file())
    except OSError:
        return []


def complete_command(text, state):
    """Snapshot matches on state 0, then return one candidate per call."""
    global _matches
    before_word = readline.get_line_buffer()[:readline.get_begidx()]
    if state == 0:
        if before_word.strip():
            _matches = matching_files(text)
        else:
            _matches = matching_commands(text)
    if state < len(_matches):
        return _matches[state] + " "
    return None


def configure_completion():
    """Connect Tab to completion on GNU Readline and macOS libedit."""
    readline.set_completer_delims(" \t\n")
    readline.set_completer(complete_command)

    backend = getattr(readline, "backend", "")
    uses_libedit = backend == "editline" or "libedit" in (readline.__doc__ or "")
    if uses_libedit:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
