#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path, PurePosixPath


def calling_user_arguments():
    if not (hasattr(os, "getuid") and hasattr(os, "getgid")):
        return []
    return ["-u", f"{os.getuid()}:{os.getgid()}"]


def folder_mount(host_folder, inside_folder, read_only=False):
    settings = f"type=bind,source={Path(host_folder).resolve()},target={inside_folder}"
    if read_only:
        settings += ",readonly"
    return ["--mount", settings]


def volume_mount(volume_name, inside_folder, read_only=False):
    settings = f"type=volume,source={volume_name},target={inside_folder}"
    if read_only:
        settings += ",readonly"
    return ["--mount", settings]


def path_inside(host_path, host_folder, inside_folder):
    relative = Path(host_path).resolve().relative_to(Path(host_folder).resolve())
    inside = PurePosixPath(inside_folder).joinpath(*relative.parts)
    return str(inside)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print the `docker run` user arguments for this machine (shared helper; "
                    "scripts import it).")
    parser.parse_args(argv)
    print(" ".join(calling_user_arguments()) or "(no -u: this system has no user ids)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
