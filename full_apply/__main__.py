#!/usr/bin/env python3
from os import isatty
from pathlib import Path
from subprocess import CalledProcessError, run
from sys import stderr, stdin
from typing import Iterable, MutableSequence, Sequence, Tuple, cast

import typer

# TODO: https://github.com/binaryornot/binaryornot/issues/626
from binaryornot.check import is_binary  # type: ignore
from yachalk import chalk

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
    cmd: str,
    path: Path,
    binary: bool,
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
    cmd: str,
    paths: Sequence[Path],
    hidden: bool = False,
    binary: bool = False,
    processed_paths=None,
    recursive: bool = False,
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
        changes += collect_changes_to_path_and_content(cmd, path, binary)
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


app = typer.Typer()


@app.command()
def main(
    cmd: str = typer.Argument(..., help="shell command to apply"),
    paths: list[str] = typer.Argument(
        ..., help="paths to apply to (recursively)"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="apply changes without asking (dangerous!)"
    ),
    no: bool = typer.Option(
        False,
        "--no",
        "-n",
        help="don't apply changes and don't even ask",
    ),
    hidden: bool = typer.Option(
        False,
        "--hidden",
        "-H",
        help='go through "hidden" (dot-prefixed) files',
    ),
    binary: bool = typer.Option(
        False,
        "--binary",
        help="go through the contents of binary files",
    ),
    recursive: bool = typer.Option(
        False, "--recursive", "-r", help="recurse into directories"
    ),
):
    """
    Apply commands to both file contents and paths.

    File paths and contents will be piped into the given shell command's
    standard input and replaced with its output.

    Examples:

    Replace all occurrences of "foo" with "bar" in both paths and file
    contents within the current directory and sub-directories (will prompt for
    confirmation before actually making any changes):

      $ full-apply -r "sed s/foo/bar/g" .
    """
    if yes and no:
        raise typer.BadParameter("can't use both --yes and --no")
    changes = collect_changes_recur(
        cmd,
        [Path(path) for path in paths],
        hidden,
        binary,
        recursive=recursive,
    )
    if not changes:
        print("no changes to be made")
        return
    for change in changes:
        print(to_term_str(change))
    conflict_paths = check_conflicts(changes)
    if conflict_paths:
        stderr.write(
            "*** CONFLICT ***\n"
            "these paths appear on both the left-hand side and right-hand \n"
            "side of the proposed changes, which is not yet supported:\n"
        )
        for conflict_path in conflict_paths:
            print(f"- {conflict_path}")
        exit(1)
    if not yes:
        if not isatty(stdin.fileno()) or no:
            print(
                "if you are happy with these changes, run with --yes "
                "or in interactive mode to apply"
            )
        else:
            apply_answer = input(chalk.bold("apply these changes (Y/[n])? "))
            if apply_answer != "Y":
                return
            yes = True
    if yes:
        print("applying changes...")
        for change in changes:
            change.apply_to_fs()
        print("all done")


def cli_main():
    typer.run(main)


if __name__ == "__main__":
    cli_main()
