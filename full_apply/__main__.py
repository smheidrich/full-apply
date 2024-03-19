#!/usr/bin/env python3
from os import isatty
from pathlib import Path
from sys import stderr, stdin

import typer
from yachalk import chalk

from .collect import check_conflicts, collect_changes_recur
from .term import to_term_str

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
    move: bool = typer.Option(True, help="move files"),
) -> None:
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
        move=move,
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


def cli_main() -> None:
    typer.run(main)


if __name__ == "__main__":
    cli_main()
