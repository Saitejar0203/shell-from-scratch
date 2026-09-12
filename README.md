# Shell in Python

A small Unix-style shell built in Python to learn operating-system basics through implementation: processes, executable lookup, working directories, environment variables, and standard input/output.

The goal is to understand what happens between typing a command and seeing its result, then build up the shell one feature at a time.

## Features

- An interactive command loop with a `$ ` prompt.
- Tab completion for builtin and executable command names in `PATH`, with a trailing space after a unique match.
- Filename completion for arguments using files in the current working directory.
- Builtins: `echo`, `exit`, `pwd`, `cd`, and `type`.
- Executable discovery through `PATH` and external program execution.
- Directory navigation using absolute paths, relative paths, and `cd ~` through `HOME`.
- Single and double quotes, adjacent quoted strings, and backslash escaping.
- Quoted executable names and filenames containing spaces.
- Standard-output redirection with `>` and `1>`, and standard-error redirection with `2>` for builtins and external programs.
- Append output with `>>` / `1>>` and append errors with `2>>`, preserving existing file contents.
- Error messages for invalid commands, failed directory changes, and unmatched quotes.

## Run locally

Use macOS or Linux with [uv](https://docs.astral.sh/uv/) installed. The project targets Python 3.14.

```sh
git clone https://github.com/Saitejar0203/shell-in-python.git
cd shell-in-python
./your_program.sh
```

Inside the shell, try:

```sh
pwd
echo 'hello    world'
type echo
type ls
ls
cd /tmp
pwd
cd ~
exit
```

## How it works

Start with [`app/main.py`](app/main.py), then follow the functions it calls:

| Module | Responsibility |
| --- | --- |
| [`app/main.py`](app/main.py) | Prompt, read input, coordinate each command, and report errors. |
| [`app/completion.py`](app/completion.py) | Configure Readline and offer command and filename completions. |
| [`app/parser.py`](app/parser.py) | Recognize words, quotes, escapes, and redirection operators; separate arguments from redirections. |
| [`app/redirection.py`](app/redirection.py) | Open output files, temporarily redirect descriptors, then restore and close them. |
| [`app/commands.py`](app/commands.py) | Handle builtins, search `PATH`, and launch external programs. |

Each command follows this path:

```text
input → parse_command → extract_redirections
      → redirect_streams → execute_command → restore streams → next prompt
```

The parser only processes text. File-descriptor changes belong to `redirection.py`, and command behavior belongs to `commands.py`.

`cd` changes the shell process's own working directory. External programs inherit its working directory, environment, and standard streams by default.

Read [Readline and command completion](docs/readline.md) for the input path, callback trace, and PATH search design.

## Local checks

Run from the repository root:

```sh
uv run python -m unittest discover -s tests -v
```

The tests launch the shell as a separate process and check file contents, output streams, and error recovery.

## Learning focus

- Distinguishing a shell from the terminal that hosts it.
- Understanding process launch, inheritance, and waiting.
- Seeing how `PATH` and `HOME` influence program behavior.
- Connecting standard streams and file descriptors to input and output.
- Separating command parsing from command execution.

## Project status

This is an evolving learning project, not a complete POSIX shell. Pipelines, job control, history, and variable expansion are not implemented yet. Multiline input and full interactive signal handling are also outside the current implementation.
