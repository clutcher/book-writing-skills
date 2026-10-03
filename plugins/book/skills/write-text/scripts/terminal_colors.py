import os
import sys

_ENABLED = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _code(value):
    return value if _ENABLED else ""


RED = _code("\033[0;31m")
GREEN = _code("\033[0;32m")
YELLOW = _code("\033[0;33m")
CYAN = _code("\033[0;36m")
BOLD = _code("\033[1m")
NC = _code("\033[0m")
