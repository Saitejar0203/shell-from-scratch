"""Interactive shell entry point: run with python -m app.main."""

import sys

from app.commands import execute_command
from app.parser import extract_redirections, parse_command
from app.redirection import redirect_streams


def report_os_error(error):
    location = f"{error.filename}: " if error.filename else ""
    print(f"shell: {location}{error.strerror}", file=sys.stderr)


def main():
    """Read, parse, redirect, execute, and repeat until exit."""
    while True:
        sys.stdout.write("$ ")
        command = input()
        try:
            tokens = parse_command(command)
            command_parts, quoted_arguments, destinations = extract_redirections(tokens)
            with redirect_streams(destinations) as ready:
                if not ready:
                    continue
                try:
                    should_exit = execute_command(command_parts, quoted_arguments)
                except OSError as error:
                    report_os_error(error)
                    should_exit = False
            if should_exit:
                break
        except ValueError as error:
            print(f"shell: {error}", file=sys.stderr)
        except OSError as error:
            report_os_error(error)


if __name__ == "__main__":
    main()
