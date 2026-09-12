"""Connect concurrent pipeline children with anonymous pipes."""

import os
import signal
import sys

from app.commands import BUILTINS, execute_command, find_executable
from app.parser import extract_redirections
from app.redirection import redirect_streams


def execute_pipeline(stages, state):
    # Validate all syntax before starting children or opening output files.
    commands = [extract_redirections(stage) for stage in stages]
    if any(not arguments for arguments, _, _ in commands):
        raise ValueError("expected command in pipeline")
    pipes = []
    children = []
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        for _ in range(len(commands) - 1):
            pipes.append(os.pipe())
        for index, (arguments, quoted, destinations) in enumerate(commands):
            pid = os.fork()
            if pid == 0:
                status = 1
                try:
                    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
                    if index:
                        os.dup2(pipes[index - 1][0], 0)
                    if index < len(pipes):
                        os.dup2(pipes[index][1], 1)
                    for read_fd, write_fd in pipes:
                        os.close(read_fd)
                        os.close(write_fd)
                    with redirect_streams(destinations) as ready:
                        if ready:
                            if arguments[0] in BUILTINS:
                                execute_command(arguments, quoted, state)
                                status = 0
                                sys.stdout.flush()
                                sys.stderr.flush()
                                os._exit(status)
                            executable = find_executable(arguments[0])
                            if executable is None:
                                print(f"{arguments[0]}: command not found", file=sys.stderr)
                                status = 127
                            else:
                                os.execv(executable, arguments)
                except (OSError, ValueError) as error:
                    print(f"shell: {error}", file=sys.stderr)
                finally:
                    sys.stdout.flush()
                    sys.stderr.flush()
                    os._exit(status)
            children.append(pid)
    finally:
        for read_fd, write_fd in pipes:
            os.close(read_fd)
            os.close(write_fd)
        for pid in children:
            os.waitpid(pid, 0)
