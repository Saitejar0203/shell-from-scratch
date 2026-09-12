"""Implement builtins and launch external programs."""

import os
import subprocess
import sys


BUILTINS = {"echo", "exit", "pwd", "type", "cd", "jobs"}


def find_executable(command_name):
    """Return the first executable file found in PATH, or None."""
    path_directories = os.environ.get("PATH", "").split(os.pathsep)

    for directory in path_directories:
        candidate_path = os.path.join(directory, command_name)
        if os.path.isfile(candidate_path) and os.access(candidate_path, os.X_OK):
            return candidate_path

    return None


def change_directory(command_parts, quoted_arguments):
    """Change this shell process's working directory."""
    if len(command_parts) != 2:
        print("cd: expected one directory argument", file=sys.stderr)
        return

    path = command_parts[1]
    if path == "~" and not quoted_arguments[1]:
        path = os.environ.get("HOME")
        if path is None:
            print("cd: HOME not set", file=sys.stderr)
            return

    try:
        os.chdir(path)
    except OSError as error:
        print(f"cd: {path}: {error.strerror}", file=sys.stderr)


def describe_command(command_parts):
    """Report whether a name is a builtin or an executable in PATH."""
    if len(command_parts) != 2:
        print("type: expected one command argument", file=sys.stderr)
        return
    command_name = command_parts[1]
    if command_name in BUILTINS:
        print(f"{command_name} is a shell builtin")
    else:
        executable_path = find_executable(command_name)
        if executable_path is not None:
            print(f"{command_name} is {executable_path}")
        else:
            print(f"{command_name}: not found")


def execute_command(command_parts, quoted_arguments):
    """Run a builtin or external program; return True only for an exit request."""
    if not command_parts:
        return False
    command_name = command_parts[0]
    if command_name == "exit":
        return True
    elif command_name == "pwd":
        print(os.getcwd())
    elif command_name == "cd":
        change_directory(command_parts, quoted_arguments)
    elif command_name == "echo":
        print(" ".join(command_parts[1:]))
    elif command_name == "jobs":
        pass  # Listing tracked jobs is introduced in a later stage.
    elif command_name == "type":
        describe_command(command_parts)
    else:
        executable_path = find_executable(command_name)

        if executable_path is not None:
            subprocess.run(command_parts, executable=executable_path)
        else:
            print(f"{command_name}: command not found", file=sys.stderr)
    return False


def start_background_job(arguments, jobs):
    """Launch an external program and retain its handle without waiting."""
    if not arguments:
        raise ValueError("expected command before &")
    if arguments[0] in BUILTINS:
        raise ValueError("background builtins are not supported yet")
    executable = find_executable(arguments[0])
    if executable is None:
        print(f"{arguments[0]}: command not found", file=sys.stderr)
        return None
    process = subprocess.Popen(arguments, executable=executable)
    job_number = len(jobs) + 1
    jobs[job_number] = process
    return job_number, process.pid
