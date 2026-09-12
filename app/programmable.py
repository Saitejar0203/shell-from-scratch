"""Registry and execution of user-provided command completers."""
import sys


class ProgrammableCompletions:
    def __init__(self):
        self.specifications = {}

    def run(self, arguments):
        if arguments and arguments[0] == "-p":
            for command in arguments[1:]:
                print(f"complete: {command}: no completion specification", file=sys.stderr)
