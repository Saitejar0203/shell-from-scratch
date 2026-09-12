"""One Readline history list for listing and interactive recall."""
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

    def run(self, arguments):
        entries = self.entries()
        start = 0
        if arguments:
            if len(arguments) != 1 or not arguments[0].isdigit():
                raise ValueError("history: expected a non-negative count")
            start = max(0, len(entries) - int(arguments[0]))
        for number, line in enumerate(entries[start:], start + 1):
            print(f"{number:5}  {line}")
