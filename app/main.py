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
    quoted_arguments = []
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
        elif character in " \t":
            if argument_started:
                arguments.append("".join(current))
                quoted_arguments.append(argument_quoted)
                current = []
                argument_started = False
                argument_quoted = False
        else:
            current.append(character)
            argument_started = True

    if quote is not None:
        raise ValueError("unmatched quote")
    if argument_started:
        arguments.append("".join(current))
        quoted_arguments.append(argument_quoted)

    # Keep quote information so cd does not expand a quoted tilde.
    return arguments, quoted_arguments


def main():
    while True:
      #TODO: Uncomment the code below to pass the first stage
      sys.stdout.write("$ ")
      # Captures the user's command in the "command" variable
      command = input()
      try:
         command_parts, quoted_arguments = parse_command(command)
      except ValueError as error:
         print(f"shell: {error}", file=sys.stderr)
         continue
      if not command_parts:
         continue

      command_name = command_parts[0]
      if command_name == "exit":
         break
      elif command_name == "pwd":
         print(os.getcwd())
      elif command_name == "cd":
         if len(command_parts) != 2:
            print("cd: expected one directory argument", file=sys.stderr)
            continue

         path = command_parts[1]
         if path == "~" and not quoted_arguments[1]:
            path = os.environ.get("HOME")
            if path is None:
               print("cd: HOME not set", file=sys.stderr)
               continue

         try:
            os.chdir(path)
         except OSError as error:
            print(f"cd: {path}: {error.strerror}", file=sys.stderr)
      elif command_name == "echo":
         print(" ".join(command_parts[1:]))
      elif command_name == "type":
         if len(command_parts) != 2:
            print("type: expected one command argument", file=sys.stderr)
            continue
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
            print(f"{command_name}: command not found")


if __name__ == "__main__":
    main()
