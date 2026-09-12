# Readline and command completion

Read this beside `app/completion.py`. This describes the current implementation.

## Who handles the keystrokes?

```text
Keyboard → terminal emulator → kernel PTY/terminal handling
                                      ↓
                      Readline inside our shell process
                      [editable line: custom|]
                                      ↓ Tab
                      complete_command("custom", 0)
                                      ↓
                      [editable line: custom_executable |]
                                      ↓ Enter
                      input() returns the finished string
                                      ↓
                      parser → redirection → command execution
```

The terminal emulator displays characters and transports input. The kernel
mediates that transport. In canonical terminal mode the kernel can collect
lines; interactive Readline uses noncanonical input to handle editing before
Enter. Its editable line buffer belongs to the shell process. These are
different buffers with different jobs. Readline is a library, not a separate
process or the command parser. Completion runs while `input()` is still waiting.

## Callback contract

- `text`: the word fragment being completed, such as `ech`.
- `state`: the zero-based candidate number for this completion attempt.
- Return a complete replacement candidate, or `None` when there are no more.

With only `echo` and `exit` matching `e`, the calls are:

| Call | Return |
| --- | --- |
| `complete_command("e", 0)` | `"echo "` |
| `complete_command("e", 1)` | `"exit "` |
| `complete_command("e", 2)` | `None` |

All three calls can happen during one Tab press. `state` is not a count of Tab
presses or an OS process state. With PATH completion enabled, additional `e`
commands may also match.

We offer every matching candidate. Under normal completion bindings a unique
match completes the word; ambiguous matches can extend a shared prefix and
require further input or another Tab to show alternatives. Exact display/bell
behavior depends on the library and configuration. We do not rank by usage or
silently choose the first candidate. Each returned full name includes a space;
a unique completion leaves the cursor ready for arguments.

## Functions and their jobs

| Function | Input / result |
| --- | --- |
| `configure_completion()` | Registers the callback and binds Tab once at interactive startup. |
| `get_line_buffer()` | Reads the current editable line. |
| `get_begidx()` | Gives the start of the word being completed. |
| `matching_commands(prefix)` | Returns sorted, unique builtin/executable names matching the prefix. |
| `complete_command(text, state)` | Returns one saved candidate plus a space, or `None`. |

Text before the current word determines the search. With only whitespace before
it, `ech<Tab>` completes a command. Otherwise, `cat re<Tab>` searches filenames
in the current working directory using `matching_paths(text)`. Files need not
be executable. Even `xyz re<Tab>` can complete to `xyz readme.txt `; an unknown
command is reported only on Enter, during execution. Directories are offered with a trailing slash and no space. Each argument
uses its own path; an earlier directory argument does not change cwd.
The delimiter setting is whitespace; it is not our quote-aware shell parser.

## Finding partial executable names

Suppose PATH is `/opt/demo/bin:/usr/bin`, and the user types `custom`.
`isfile("/opt/demo/bin/custom")` checks that exact filename; it cannot discover
`custom_executable`. Instead:

1. Split PATH into directory entries.
2. Scan each directory's immediate entries with `os.scandir`.
3. Filter names using `startswith("custom")`.
4. Keep files for which `os.access(entry.path, os.X_OK)` succeeds.
5. Combine them with matching builtins in a set, then sort.

An empty PATH entry represents the current directory. Missing, unreadable,
or non-directory PATH entries are skipped. Directories and non-executable
files are not offered; valid executable symlinks can be offered. Duplicate
names across directories appear once. At execution time the ordinary PATH
lookup chooses the first usable executable in PATH order.

At `state == 0`, the callback takes a new candidate snapshot. Later states read
that list rather than rescanning every directory. A later Tab attempt rescans,
so changes to PATH or its files can be reflected. Completion is a suggestion:
a file can disappear or lose permission before execution.

## Completing paths in any argument

`completion_candidates(text)` selects the search; `complete_command` only
caches and enumerates its replacements. `matching_paths(text)` splits at the
last slash and scans that directory, preserving the path the user typed:

| Input fragment | Directory searched | Name prefix | Example replacement |
| --- | --- | --- | --- |
| `re` | `.` | `re` | `readme.txt ` |
| `path/to/f` | `path/to/` | `f` | `path/to/file.txt ` |
| `./proj` | `./` | `proj` | `./project/` |
| `/tmp/data/` | `/tmp/data/` | empty | `/tmp/data/report.txt ` |

Files end in a space; directories end in `/`. Readline uses the full candidate
set for common prefixes and displays alternatives on repeated Tab presses.
With `xyz_foo/` and `xyz_foo_bar/`, their shared prefix stops at `xyz_foo`, so no
slash is inserted until the match is unique. Missing/unreadable directories
produce no candidates. A no-match attempt preserves the line and rings a bell.

In `ls bar/ f<Tab>`, `f` searches cwd, not `bar/`. The same selection works for
second, third, and later arguments, including after unknown command names.

## Portability and tests

Python's `readline` module can wrap GNU Readline or macOS libedit. We detect the
backend and use `tab: complete` for GNU Readline or `bind ^I rl_complete` for
libedit. Setup happens only when stdin and stdout are terminals. A small
libedit compatibility branch emits a no-match bell explicitly, because that
backend can omit it after a preceding completion. GNU Readline supplies its
own bell.

Tests cover candidate filtering, duplicates, refreshed snapshots, argument
position, nested paths, directory suffixes, missing matches, repeated-Tab
listings, progressive common prefixes, and actual execution through a PTY. They do
not establish full Bash behavior. Escaping special characters in suggested names and configurable usage ranking are
outside this implementation.

## References

- [Python Readline interface](https://docs.python.org/3/library/readline.html)
- [Python directory scanning](https://docs.python.org/3/library/os.html#os.scandir)
- [GNU Readline completion](https://www.gnu.org/software/bash/manual/html_node/Commands-For-Completion.html)
- [Linux terminal modes](https://man7.org/linux/man-pages/man3/termios.3.html)
