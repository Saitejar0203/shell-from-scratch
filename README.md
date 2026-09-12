# Shell in Python

A small Unix-style shell built in Python to learn operating-system basics through implementation: processes, executable lookup, working directories, environment variables, and standard input/output.

The goal is to understand what happens between typing a command and seeing its result, then build up the shell one feature at a time.

## Features

- An interactive command loop with a `$ ` prompt.
- Builtins: `echo`, `exit`, `pwd`, `cd`, and `type`.
- Executable discovery through `PATH` and external program execution.
- Directory navigation using absolute paths, relative paths, and `cd ~` through `HOME`.
- Single and double quotes, adjacent quoted strings, and backslash escaping.
- Quoted executable names and filenames containing spaces.
- Standard-output redirection with `>` and `1>`, and standard-error redirection with `2>` for builtins and external programs.
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

The implementation is in [`app/main.py`](app/main.py):

1. `parse_command()` turns input into arguments while tracking quotes and escapes.
2. `main()` handles builtins within the shell process.
3. `find_executable()` searches the directories listed in `PATH`.
4. `subprocess.run()` launches external programs and waits for them to finish.

`cd` changes the shell process's own working directory. External programs inherit its working directory, environment, and standard streams by default.

## Learning focus

- Distinguishing a shell from the terminal that hosts it.
- Understanding process launch, inheritance, and waiting.
- Seeing how `PATH` and `HOME` influence program behavior.
- Connecting standard streams and file descriptors to input and output.
- Separating command parsing from command execution.

## Project status

This is an evolving learning project, not a complete POSIX shell. Appending output, pipelines, job control, history, and variable expansion are not implemented yet. Multiline input and full interactive signal handling are also outside the current implementation.
