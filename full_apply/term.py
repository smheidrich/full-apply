from difflib import diff_bytes, unified_diff
from functools import singledispatch

from yachalk import chalk

from .change import ContentChange, PathChange


@singledispatch
def prefix_line(obj, prefix=""):
    raise NotImplementedError(f"no prefix_line impl for type '{type(obj)}'")


@prefix_line.register
def _(obj: str, prefix: str = ""):
    return f"{prefix}{obj}"


@prefix_line.register
def _(obj: bytes, prefix: bytes = b""):
    return prefix + obj


@singledispatch
def prefix_lines(obj, prefix="", first_line_prefix=None):
    raise NotImplementedError(f"no prefix_lines impl for type '{type(obj)}'")


@prefix_lines.register
def _(obj: list, prefix: str | bytes = "", first_line_prefix=None):
    if first_line_prefix is None:
        first_line_prefix = prefix
    return [prefix_line(line, first_line_prefix) for line in obj[:1]] + [
        prefix_line(line, prefix) for line in obj[1:]
    ]


@prefix_lines.register
def _(obj: str, prefix: str = "", first_line_prefix=None):
    return prefix_lines(
        obj.splitlines(keepends=True), prefix, first_line_prefix
    )


@prefix_lines.register
def _(obj: bytes, prefix: bytes = b"", first_line_prefix=None):
    return prefix_lines(
        obj.splitlines(keepends=True), prefix, first_line_prefix
    )


def color_diff_line(line: str) -> str:
    if line.startswith("+"):
        return chalk.green(line.rstrip("\n")) + "\n"
    elif line.startswith("-"):
        return chalk.red(line.rstrip("\n")) + "\n"
    return line


@singledispatch
def to_term_str(obj) -> str:
    raise TypeError(
        f"no terminal output string formatting for type '{type(obj)}'"
    )


@to_term_str.register
def _(obj: PathChange) -> str:
    s = (
        chalk.bold.yellow("move")
        + f"  {obj.old} "
        + chalk.bold("→")
        + f" {obj.new}"
    )
    if obj.old_is_dir:
        s += chalk.red("\nattn:") + " will be ignored (dirs not yet supported)"
    if obj.replace_cmd_stderr:
        s += chalk.grey("\nnote: ") + "".join(
            prefix_lines(
                obj.replace_cmd_stderr.decode("utf-8"),
                "      ",
                first_line_prefix="",
            )
        )
    return s.rstrip("\n")


@to_term_str.register
def _(obj: ContentChange) -> str:
    content_diff = diff_bytes(
        unified_diff,
        obj.old.splitlines(keepends=True),
        obj.new.splitlines(keepends=True),
        fromfile=b"old",
        tofile=b"new",
    )
    s = chalk.bold.yellow("patch ") + f"{obj.path}:\n"
    # skip first 2 lines which are just +++ ---
    next(content_diff)
    next(content_diff)
    for diff_line in content_diff:
        s += "        " + color_diff_line(diff_line.decode("utf-8"))
    if obj.replace_cmd_stderr:
        s += chalk.grey("note: ") + "".join(
            prefix_lines(
                obj.replace_cmd_stderr.decode("utf-8"),
                "      ",
                first_line_prefix="",
            )
        )
    return s.rstrip("\n")
