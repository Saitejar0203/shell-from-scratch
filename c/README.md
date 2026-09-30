# Shell from Scratch — C

I’m building a shell in C to understand processes, file descriptors, parsing, and memory ownership at a low level, so I can become better at building systems.

All 76 currently available CodeCrafters shell stages are implemented and submitted, including completion, background jobs, pipelines, persistent history, and shell variables.

## Run

Requires a C compiler, CMake, and Readline development headers/library (macOS includes a compatible libedit interface).

```sh
./your_program.sh
```

## Code map

- `src/main.c`: builtins, executable lookup, forks, pipes, and descriptor redirection.
- `src/parser.c`: words, operators, quotes, escapes, and variable expansion.
- `src/completion.c`: command, filename, and programmable completion.
- `src/jobs.c`: background process tracking and reaping.
- `src/history.c`: command recall, file loading, and incremental persistence.
- `src/variables.c`: shell-local variables and declaration validation.

## Checks

```sh
python3 -m unittest discover -s tests -v
```

This is an educational shell with the challenge’s feature set. Full POSIX compatibility, multiline syntax, background pipelines, signal-based interactive job control, and concurrent history merging are outside its scope.
