"""Supply command and filename candidates to the line editor."""

import os
import readline
import shlex
import sys

from app.commands import BUILTINS


_matches = []
_programmable = None


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


def matching_paths(text):
    """Complete the last path component while preserving the typed directory."""
    directory, separator, prefix = text.rpartition("/")
    typed_directory = directory + separator
    search_directory = typed_directory or "."
    matches = []
    try:
        with os.scandir(search_directory) as entries:
            for entry in entries:
                if not entry.name.startswith(prefix):
                    continue
                candidate = typed_directory + entry.name
                if entry.is_dir():
                    matches.append(candidate + "/")
                elif entry.is_file():
                    matches.append(candidate + " ")
    except OSError:
        return []
    return sorted(matches)


def completion_candidates(text):
    """Choose command lookup for the first word, path lookup for any argument."""
    before_word = readline.get_line_buffer()[:readline.get_begidx()]
    if before_word.strip():
        try:
            words = shlex.split(before_word)
        except ValueError:
            words = before_word.split()
        if words and _programmable is not None and words[0] in _programmable.specifications:
            previous = words[-1] if len(words) > 1 else ""
            return [name + " " for name in _programmable.candidates(words[0], text, previous)]
        return matching_paths(text)
    return [name + " " for name in matching_commands(text)]


def complete_command(text, state):
    """Snapshot replacements once per Tab attempt, then enumerate them."""
    global _matches
    if state == 0:
        _matches = completion_candidates(text)
        # libedit can omit the no-match bell after a preceding completion.
        if not _matches and using_libedit():
            sys.stdout.write("\a")
            sys.stdout.flush()
    if state < len(_matches):
        return _matches[state]
    return None


def using_libedit():
    """Python may expose GNU Readline or its macOS libedit compatibility API."""
    return (getattr(readline, "backend", "") == "editline"
            or "libedit" in (readline.__doc__ or ""))


def configure_completion(programmable=None):
    """Connect Tab to completion on GNU Readline and macOS libedit."""
    global _programmable
    _programmable = programmable
    readline.set_completer_delims(" \t\n")
    readline.set_completer(complete_command)

    if using_libedit():
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
