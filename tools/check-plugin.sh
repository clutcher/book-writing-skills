#!/usr/bin/env bash
PYTHONDONTWRITEBYTECODE=1 exec python3 -B "$(dirname "$0")/check-plugin.py" "$@"
