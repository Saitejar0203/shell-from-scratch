"""Shell-local variables and the declare builtin."""
import re
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
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                print(f"declare: `{assignment}': not a valid identifier", file=sys.stderr)
                continue
            if separator:
                self.values[name] = value
            else:
                self.values.setdefault(name, "")


def expansion_at(command, index, values):
    """Return (replacement, consumed length), or None for a literal dollar."""
    match = re.match(r"\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})", command[index:])
    if match is None:
        return None
    return values.get(match[1] or match[2], ""), len(match[0])
