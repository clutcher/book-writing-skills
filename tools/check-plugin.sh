#!/usr/bin/env bash
PYTHONDONTWRITEBYTECODE=1 exec python3 "$(dirname "$0")/check-plugin.py" "$@"
