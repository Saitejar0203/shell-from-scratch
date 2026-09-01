import os
import sys


def main():
    while True:
      #TODO: Uncomment the code below to pass the first stage
      sys.stdout.write("$ ")
      # Captures the user's command in the "command" variable
      command = input()
      if command == "exit":
         break
      elif command.startswith("echo "):
         print(command[5:])
      elif command.startswith("type "):
         command_name = command[5:]
         if command_name in ("echo", "exit", "type"):
            print(f"{command_name} is a shell builtin")
         else:
            executable_path = None
            path_directories = os.environ.get("PATH", "").split(os.pathsep)

            for directory in path_directories:
               candidate_path = os.path.join(directory, command_name)
               if os.path.isfile(candidate_path) and os.access(candidate_path, os.X_OK):
                  executable_path = candidate_path
                  break

            if executable_path is not None:
               print(f"{command_name} is {executable_path}")
            else:
               print(f"{command_name}: not found")
      else:
         # Prints the "<command>: command not found" message
         print(f"{command}: command not found")


if __name__ == "__main__":
    main()
