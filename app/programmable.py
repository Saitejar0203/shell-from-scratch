"""Registry and execution of user-provided command completers."""
import subprocess
import sys


class ProgrammableCompletions:
    def __init__(self):
        self.specifications = {}

    def run(self, arguments):
        if arguments and arguments[0] == "-p":
            for command in arguments[1:]:
                if command in self.specifications:
                    path = self.specifications[command].replace("'", "'\\''")
                    print(f"complete -C '{path}' {command}")
                else:
                    print(f"complete: {command}: no completion specification", file=sys.stderr)
        elif arguments and arguments[0] == "-C":
            if len(arguments) < 3:
                raise ValueError("complete: -C requires a script and command")
            for command in arguments[2:]:
                self.specifications[command] = arguments[1]
        else:
            raise ValueError("complete: expected -C or -p")

    def candidates(self, command, text):
        """Wait for the completer and interpret stdout as candidate lines."""
        try:
            result = subprocess.run([self.specifications[command]],
                                    stdout=subprocess.PIPE, text=True)
        except OSError:
            return []
        return sorted({line for line in result.stdout.splitlines()
                       if line and line.startswith(text)})
