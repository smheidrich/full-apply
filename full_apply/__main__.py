#!/usr/bin/env python3
from abc import ABC, abstractmethod
from difflib import diff_bytes, unified_diff
from pathlib import Path
from subprocess import CalledProcessError, run
from sys import argv, stderr
from typing import Sequence, Tuple

from yachalk import chalk

from .term import color_diff_line, prefix_lines

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


class Change(ABC):
    replace_cmd_stderr: bytes

    @abstractmethod
    def apply(self):
        ...


class PathChange(Change):
    def __init__(self, old: Path, new: Path, replace_cmd_stderr: bytes):
        self.old = old
        self.new = new
        self.replace_cmd_stderr = replace_cmd_stderr

    def apply(self):
        self.old.rename(self.new)

    def __str__(self):
        s = (
            chalk.bold.yellow("move")
            + f"  {self.old} "
            + chalk.bold("→")
            + f" {self.new}"
        )
        if self.replace_cmd_stderr:
            s += chalk.grey("\nnote: ") + "".join(
                prefix_lines(
                    self.replace_cmd_stderr.decode("utf-8"),
                    "      ",
                    first_line_prefix="",
                )
            )
        return s.rstrip("\n")


class ContentChange(Change):
    def __init__(
        self, path: Path, old: bytes, new: bytes, replace_cmd_stderr: bytes
    ):
        self.path = path
        self.old = old
        self.new = new
        self.replace_cmd_stderr = replace_cmd_stderr

    def apply(self):
        self.path.write_bytes(self.new)

    def __str__(self):
        content_diff = diff_bytes(
            unified_diff,
            self.old.splitlines(keepends=True),
            self.new.splitlines(keepends=True),
            fromfile=b"old",
            tofile=b"new",
        )
        s = chalk.bold.yellow("patch ") + f"{self.path}:\n"
        next(content_diff)
        next(content_diff)
        for diff_line in content_diff:
            s += "        " + color_diff_line(diff_line.decode("utf-8"))
        if self.replace_cmd_stderr:
            s += chalk.grey("note: ") + "".join(
                prefix_lines(
                    self.replace_cmd_stderr.decode("utf-8"),
                    "      ",
                    first_line_prefix="",
                )
            )
        return s.rstrip("\n")


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
        print(change)
