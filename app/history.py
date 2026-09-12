"""One Readline history list for listing and interactive recall."""
from pathlib import Path
import readline


class History:
    def __init__(self):
        readline.clear_history()
        readline.set_auto_history(False)

    def record(self, line):
        if line.strip():
            readline.add_history(line)

    def entries(self):
        return [readline.get_history_item(i) for i in
                range(1, readline.get_current_history_length() + 1)]

    def read(self, path):
        for line in Path(path).read_text().splitlines():
            if line.strip():
                readline.add_history(line)

    def write(self, path):
        Path(path).write_text("".join(line + "\n" for line in self.entries()))

    def run(self, arguments):
        if arguments and arguments[0] in ("-r", "-w"):
            if len(arguments) != 2:
                raise ValueError(f"history: {arguments[0]} requires a path")
            action = self.read if arguments[0] == "-r" else self.write
            action(arguments[1])
            return
        entries = self.entries()
        start = 0
        if arguments:
            if len(arguments) != 1 or not arguments[0].isdigit():
                raise ValueError("history: expected a non-negative count")
            start = max(0, len(entries) - int(arguments[0]))
        for number, line in enumerate(entries[start:], start + 1):
            print(f"{number:5}  {line}")
