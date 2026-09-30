# Shell from Scratch

I’m building a Unix-style shell in Python and C from scratch to deepen my understanding of low-level CS fundamentals and become better at building systems. I’m exploring processes, executable lookup, working directories, environment variables, and standard input/output.

The goal is to understand what happens between typing a command and seeing its result, then build up the shell one feature at a time.

The implementations live in `python/` and `c/`. Each language has its own CodeCrafters submission checkout; this repository keeps them together for comparison.

## Implementations

Both languages cover all 76 currently available CodeCrafters shell stages: builtins, external processes, navigation, quoting, redirection, command/file/programmable completion, background jobs, pipelines, persistent history, and shell-local variables.

- [Python](python/): source in `app/`, behavioral tests in `tests/`, and [Readline notes](python/docs/readline.md).
- [C](c/): source in `src/`, with explicit process, descriptor, and memory management.

Each exercise has its own commit and was submitted to CodeCrafters. The original Python history is preserved.

## Run locally

```sh
git clone https://github.com/Saitejar0203/shell-from-scratch.git
cd shell-from-scratch
```

Python requires [uv](https://docs.astral.sh/uv/) and targets Python 3.14:

```sh
cd python
./your_program.sh
uv run python -m unittest discover -s tests -v
```

C requires a compiler, CMake, and Readline development headers/library. macOS includes a compatible libedit interface:

```sh
cd c
./your_program.sh
python3 -m unittest discover -s tests -v
```

The source modules separate parsing, execution, completion, history, jobs, and variables. A command follows this path:

```text
input → record history → parse words/operators/expansions
      → single command: redirect → execute → restore
      → pipeline: wire pipes → launch all children → wait
      → report completed background jobs → next prompt
```

## Learning focus

- Distinguishing a shell from the terminal that hosts it.
- Understanding process launch, inheritance, and waiting.
- Seeing how `PATH` and `HOME` influence program behavior.
- Connecting standard streams and file descriptors to input and output.
- Separating command parsing from command execution.

## Project status

Both implementations cover all currently available CodeCrafters shell exercises. This remains a learning shell rather than a complete POSIX shell. Background pipelines/builtins, full interactive signal job control, multiline input, arbitrary shell expansion, and concurrent history merging are outside the exercise scope. Background jobs support listing, completion notifications, reaping, and number recycling.
