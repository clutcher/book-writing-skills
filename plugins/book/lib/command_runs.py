#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from dataclasses import dataclass

TIMED_OUT_EXIT = 124


@dataclass
class CommandResult:
    exit_code: int
    output: str
    timed_out: bool = False
    error_output: str = ""

    @property
    def passed(self):
        return self.exit_code == 0 and not self.timed_out

    def last_line(self, width=None):
        lines = [line for line in self.output.splitlines() if line.strip()]
        line = lines[-1] if lines else ""
        return line[:width] if width else line


def python_command(script, *arguments):
    return [sys.executable, str(script), *[str(argument) for argument in arguments]]


def quiet_environment(extra=None):
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    environment.update(extra or {})
    return environment


def run_command(command, time_limit, cwd=None, environment=None, keep_error_output=True):
    try:
        completed = subprocess.run(
            [str(part) for part in command], cwd=cwd, env=environment or quiet_environment(),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if keep_error_output else subprocess.PIPE,
            encoding="utf-8", errors="replace", timeout=time_limit)
    except subprocess.TimeoutExpired as stopped:
        caught = stopped.output or ""
        if isinstance(caught, bytes):
            caught = caught.decode("utf-8", errors="replace")
        return CommandResult(TIMED_OUT_EXIT, caught, timed_out=True)
    except OSError as error:
        return CommandResult(127, f"could not start {command[0]}: {error}")
    return CommandResult(completed.returncode, completed.stdout or "",
                         error_output=completed.stderr or "")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run one command with a time limit and print its exit code and last line "
                    "(shared helper; runner scripts import it).")
    parser.add_argument("--time-limit", type=int, default=60, help="seconds (default 60)")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="the command to run")
    arguments = parser.parse_args(argv)
    if not arguments.command:
        parser.print_help()
        return 0
    result = run_command(arguments.command, arguments.time_limit)
    state = "TIMED OUT" if result.timed_out else f"exit {result.exit_code}"
    print(f"{state} :: {result.last_line(100)}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
