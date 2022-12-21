#!/usr/bin/env python3
from pathlib import Path
from subprocess import CalledProcessError, run
from sys import stderr
from typing import MutableSequence, Sequence, Tuple

import typer

from .change import Change, ContentChange, PathChange
from .term import to_term_str


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
    cmd: str, path: Path
) -> Sequence[Change]:
    changes: MutableSequence[Change] = []
    # apply to contents
    if path.is_file():
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
    # apply to path
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
    cmd: str, paths: Sequence[Path], hidden: bool = False, processed_paths=None
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
        changes += collect_changes_to_path_and_content(cmd, path)
        if path.is_dir():
            for subpath in path.iterdir():
                changes += collect_changes_recur(
                    cmd, [subpath], hidden, processed_paths
                )
        processed_paths.add(path)
    return changes


app = typer.Typer()


@app.command()
def main(
    cmd: str = typer.Argument(..., help="shell command to apply"),
    paths: list[str] = typer.Argument(
        ..., help="paths to apply to (recursively)"
    ),
    yes: bool = typer.Option(
        False, help="actually apply instead of performing a dry-run"
    ),
    hidden: bool = typer.Option(
        False, help='whether to go through "hidden" (dot-prefixed) files'
    ),
):
    """
    Apply commands to both file contents and paths.

    File paths and contents will be piped into the given shell command's
    standard input and replaced with its output.

    Examples:

    Replace all occurrences of "foo" with "bar" in both paths and file
    contents within the current directory and sub-directories:

      $ full-apply "sed s/foo/bar/g" .
    """
    changes = collect_changes_recur(
        cmd, [Path(path) for path in paths], hidden
    )
    if not changes:
        print("no changes to be made")
        return
    for change in changes:
        print(to_term_str(change))
        if yes:
            change.apply_to_fs()
    if not yes:
        print("if you are happy with these changes, run with --yes to apply")
    else:
        print("all done")


def cli_main():
    typer.run(main)


if __name__ == "__main__":
    cli_main()
