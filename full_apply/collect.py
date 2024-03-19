#!/usr/bin/env python3
from pathlib import Path
from subprocess import CalledProcessError, run
from sys import stderr
from typing import Iterable, MutableSequence, Sequence, Tuple, cast

# TODO: https://github.com/binaryornot/binaryornot/issues/626
from binaryornot.check import is_binary  # type: ignore

from .change import Change, ContentChange, PathChange


def run_replace_cmd(cmd: str, buf: bytes) -> Tuple[bytes, bytes]:
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


def collect_changes_to_path_and_content(
    cmd: str,
    path: Path,
    binary: bool,
    move: bool,
) -> Sequence[Change]:
    changes: MutableSequence[Change] = []
    # apply to contents
    if path.is_file() and (binary or not is_binary(str(path))):
        content_bytes = path.read_bytes()
        new_content_bytes, replace_cmd_stderr = run_replace_cmd(
            cmd, content_bytes
        )
        if new_content_bytes != content_bytes:
            changes.append(
                ContentChange(
                    path, content_bytes, new_content_bytes, replace_cmd_stderr
                )
            )
    # apply to path (skipped if `move` is False)
    if move:
        path_str = str(path)
        new_path_bytes, replace_cmd_stderr = run_replace_cmd(
            cmd, path_str.encode("utf-8")
        )
        new_path_str = new_path_bytes.decode("utf-8")
        new_path = Path(new_path_str)
        if new_path_str != path_str:
            changes.append(
                PathChange(
                    path,
                    new_path,
                    new_path.exists(),
                    path.is_dir(),
                    replace_cmd_stderr,
                )
            )
    return changes


def collect_changes_recur(
    cmd: str,
    paths: Sequence[Path],
    hidden: bool = False,
    binary: bool = False,
    processed_paths=None,
    recursive: bool = False,
    move: bool = True,
) -> Sequence[Change]:
    # avoid processing paths twice:
    if processed_paths is None:
        processed_paths = set()
    changes: MutableSequence[Change] = []
    for path in paths:
        if path in processed_paths or (
            path.name.startswith(".") and not hidden
        ):
            continue
        changes += collect_changes_to_path_and_content(cmd, path, binary, move)
        if path.is_dir():
            if recursive:
                for subpath in path.iterdir():
                    changes += collect_changes_recur(
                        cmd,
                        [subpath],
                        hidden,
                        binary,
                        processed_paths,
                        recursive=recursive,
                        move=move,
                    )
            else:
                # TODO this is a horrible solution, but proper dir handling
                #      will require complete restructure anyway...
                if changes:
                    dir_change = cast(PathChange, changes[-1])
                    dir_change.recursion_skipped = True
        processed_paths.add(path)
    return changes


def check_conflicts(changes: Sequence[Change]) -> Iterable[Path]:
    lhss = set()
    rhss = set()
    for change in changes:
        if isinstance(change, PathChange):
            lhss.add(change.old)
            rhss.add(change.new)
        elif isinstance(change, ContentChange):
            lhss.add(change.path)
        else:
            assert False, f"should never happen: {change} is not a Change obj"
    return lhss.intersection(rhss)
