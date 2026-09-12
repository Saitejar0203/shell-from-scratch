"""Shell-local variables and the declare builtin."""
import sys


class Variables:
    def __init__(self):
        self.values = {}

    def declare(self, arguments):
        if arguments and arguments[0] == "-p":
            for name in arguments[1:]:
                print(f"declare: {name}: not found", file=sys.stderr)
