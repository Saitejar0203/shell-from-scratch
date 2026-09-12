"""Supply builtin command candidates to the interactive line editor."""

import readline

from app.commands import BUILTINS


def complete_builtin(text, state):
    """Return candidate number state, or None when no candidates remain."""
    # Only complete the first word, not an argument later in the line.
    before_word = readline.get_line_buffer()[:readline.get_begidx()]
    if before_word.strip():
        return None

    matches = sorted(name for name in BUILTINS if name.startswith(text))
    if state < len(matches):
        return matches[state] + " "
    return None


def configure_completion():
    """Connect Tab to completion on GNU Readline and macOS libedit."""
    readline.set_completer_delims(" \t\n")
    readline.set_completer(complete_builtin)

    backend = getattr(readline, "backend", "")
    uses_libedit = backend == "editline" or "libedit" in (readline.__doc__ or "")
    if uses_libedit:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
