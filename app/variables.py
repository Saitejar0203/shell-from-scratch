"""Shell-local variables and the declare builtin."""
import sys


class Variables:
    def __init__(self):
        self.values = {}

    def declare(self, arguments):
        if arguments and arguments[0] == "-p":
            for name in arguments[1:]:
                if name in self.values:
                    value = self.values[name]
                    # Print reusable double-quoted shell text.
                    for character in ('\\', '"', '$', '`'):
                        value = value.replace(character, '\\' + character)
                    print(f'declare -- {name}="{value}"')
                else:
                    print(f"declare: {name}: not found", file=sys.stderr)
            return
        for assignment in arguments:
            name, separator, value = assignment.partition("=")
            if separator:
                self.values[name] = value
            else:
                self.values.setdefault(name, "")
