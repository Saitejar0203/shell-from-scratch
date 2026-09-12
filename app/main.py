from contextlib import contextmanager
import os 
import subprocess
import sys 


def find_executable(command_name):
    path_directories = os.environ.get("PATH", "").split(os.pathsep)

    for directory in path_directories:
        candidate_path = os.path.join(directory, command_name)
        if os.path.isfile(candidate_path) and os.access(candidate_path, os.X_OK):
            return candidate_path

    return None


def parse_command(command):
    arguments = []
    current = []
    quote = None
    argument_started = False
    argument_quoted = False

    characters = iter(command)
    for character in characters:
        if quote is not None:
            if character == quote:
                quote = None
            elif quote == '"' and character == "\\":
                escaped = next(characters, None)
                if escaped is None:
                    raise ValueError("unmatched quote")
                if escaped not in '\\"$`':
                    current.append("\\")
                current.append(escaped)
            else:
                current.append(character)
        elif character == "\\":
            escaped = next(characters, None)
            if escaped is None:
                raise ValueError("trailing backslash")
            current.append(escaped)
            argument_started = True
            argument_quoted = True
        elif character in "\"'":
            quote = character
            argument_started = True
            argument_quoted = True
        elif character == ">":
            word = "".join(current)
            if argument_started and not argument_quoted and word.isdecimal():
                if word != "1":
                    raise ValueError("only stdout redirection is supported")
            elif argument_started:
                arguments.append(("word", word, argument_quoted))
            arguments.append(("redirect_stdout", ">", False))
            current = []
            argument_started = False
            argument_quoted = False
        elif character in " \t":
            if argument_started:
                arguments.append(("word", "".join(current), argument_quoted))
                current = []
                argument_started = False
                argument_quoted = False
        else:
            current.append(character)
            argument_started = True

    if quote is not None:
        raise ValueError("unmatched quote")
    if argument_started:
        arguments.append(("word", "".join(current), argument_quoted))

    # Each token retains its kind, text, and quote information.
    return arguments


def extract_redirections(tokens):
    arguments = []
    quoted_arguments = []
    destinations = []
    index = 0
    while index < len(tokens):
        kind, value, quoted = tokens[index]
        if kind == "redirect_stdout":
            index += 1
            if index == len(tokens) or tokens[index][0] != "word":
                raise ValueError("expected filename after >")
            destinations.append(tokens[index][1])
        else:
            arguments.append(value)
            quoted_arguments.append(quoted)
        index += 1
    return arguments, quoted_arguments, destinations


@contextmanager
def redirect_stdout(destinations):
    if not destinations:
        yield
        return

    sys.stdout.flush()
    saved_stdout = os.dup(1)
    try:
        for path in destinations:
            with open(path, "w") as output_file:
                os.dup2(output_file.fileno(), 1)
        yield
    finally:
        try:
            sys.stdout.flush()
        finally:
            try:
                os.dup2(saved_stdout, 1)
            finally:
                os.close(saved_stdout)


def execute_command(command_parts, quoted_arguments):
    if not command_parts:
        return False
    command_name = command_parts[0]
    if command_name == "exit":
        return True
    elif command_name == "pwd":
        print(os.getcwd())
    elif command_name == "cd":
        if len(command_parts) != 2:
            print("cd: expected one directory argument", file=sys.stderr)
            return False

        path = command_parts[1]
        if path == "~" and not quoted_arguments[1]:
            path = os.environ.get("HOME")
            if path is None:
                print("cd: HOME not set", file=sys.stderr)
                return False

        try:
            os.chdir(path)
        except OSError as error:
            print(f"cd: {path}: {error.strerror}", file=sys.stderr)
    elif command_name == "echo":
        print(" ".join(command_parts[1:]))
    elif command_name == "type":
        if len(command_parts) != 2:
            print("type: expected one command argument", file=sys.stderr)
            return False
        command_name = command_parts[1]
        if command_name in ("echo", "exit", "pwd", "type", "cd"):
            print(f"{command_name} is a shell builtin")
        else:
            executable_path = find_executable(command_name)
            if executable_path is not None:
                print(f"{command_name} is {executable_path}")
            else:
                print(f"{command_name}: not found")
    else:
        executable_path = find_executable(command_name)

        if executable_path is not None:
            subprocess.run(command_parts, executable=executable_path)
        else:
            print(f"{command_name}: command not found", file=sys.stderr)
    return False

def main():
    while True:
        sys.stdout.write("$ ")
        command = input()
        try:
            tokens = parse_command(command)
            command_parts, quoted_arguments, destinations = extract_redirections(tokens)
            with redirect_stdout(destinations):
                should_exit = execute_command(command_parts, quoted_arguments)
            if should_exit:
                break
        except ValueError as error:
            print(f"shell: {error}", file=sys.stderr)
        except OSError as error:
            location = f"{error.filename}: " if error.filename else ""
            print(f"shell: {location}{error.strerror}", file=sys.stderr)


if __name__ == "__main__":
    main()
