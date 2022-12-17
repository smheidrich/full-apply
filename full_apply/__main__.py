#!/usr/bin/env python3
from pathlib import Path
from subprocess import CalledProcessError, run
from sys import argv, stderr
from typing import Sequence, Tuple

from .change import Change, ContentChange, PathChange
from .term import to_term_str

cmd = argv[1]
path = argv[2]


def run_replace_cmd(buf: bytes) -> Tuple[bytes, bytes]:
    try:
        r = run(
            cmd,
            input=buf,
            shell=True,
            capture_output=True,
            check=True,
        )
    except CalledProcessError as e:
        stderr.write(f"*** ERROR running '{cmd}' ***\n")
        stderr.buffer.write(e.stderr)
        if e.stdout:
            stderr.write("output was:\n")
            stderr.buffer.write(e.stdout)
        exit(1)
    return r.stdout, r.stderr


def collect_changes_to_path_and_content(path: Path) -> Sequence[Change]:
    changes = []
    # apply to contents
    if path.is_file():
        content_bytes = path.read_bytes()
        new_content_bytes, replace_cmd_stderr = run_replace_cmd(content_bytes)
        if new_content_bytes != content_bytes:
            changes.append(
                ContentChange(
                    path, content_bytes, new_content_bytes, replace_cmd_stderr
                )
            )
    # apply to path
    path_str = str(path)
    new_path_bytes, replace_cmd_stderr = run_replace_cmd(
        path_str.encode("utf-8")
    )
    new_path_str = new_path_bytes.decode("utf-8")
    if new_path_str != path_str:
        changes.append(
            PathChange(path, Path(new_path_str), replace_cmd_stderr)
        )
    return changes


def collect_changes_recur(path: Path):
    changes = collect_changes_to_path_and_content(path)
    if path.is_dir():
        for subpath in path.iterdir():
            changes += collect_changes_recur(subpath)
    return changes


if __name__ == "__main__":
    changes = collect_changes_recur(Path(path))
    for change in changes:
        print(to_term_str(change))
