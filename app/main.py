"""Interactive shell entry point: run with python -m app.main."""

import sys

from app.commands import execute_command, list_jobs, start_background_job
from app.completion import configure_completion
from app.parser import extract_background, extract_redirections, parse_command, split_pipeline
from app.history import History
from app.pipeline import execute_pipeline
from app.redirection import redirect_streams


def report_os_error(error):
    location = f"{error.filename}: " if error.filename else ""
    print(f"shell: {location}{error.strerror}", file=sys.stderr)


def main():
    """Read, parse, redirect, execute, and repeat until exit."""
    if sys.stdin.isatty() and sys.stdout.isatty():
        configure_completion()
    jobs = {}
    history = History()
    try:
        history.load()
    except OSError as error:
        report_os_error(error)
    while True:
        list_jobs(jobs, completed_only=True)
        try:
            command = input("$ ")
        except EOFError:
            break
        history.record(command)
        try:
            tokens, background = extract_background(parse_command(command))
            stages = split_pipeline(tokens)
            if len(stages) > 1:
                if background:
                    raise ValueError("background pipelines are not supported")
                execute_pipeline(stages, jobs, history)
                continue
            started_job = None
            should_exit = False
            command_parts, quoted_arguments, destinations = extract_redirections(tokens)
            with redirect_streams(destinations) as ready:
                if not ready:
                    continue
                try:
                    if background:
                        started_job = start_background_job(command_parts, jobs, command)
                    else:
                        should_exit = execute_command(command_parts, quoted_arguments, jobs, history)
                except OSError as error:
                    report_os_error(error)
                    should_exit = False
            if started_job is not None:
                job_number, pid = started_job
                print(f"[{job_number}] {pid}")
            if should_exit:
                break
        except ValueError as error:
            print(f"shell: {error}", file=sys.stderr)
        except OSError as error:
            report_os_error(error)


if __name__ == "__main__":
    main()
