#!/usr/bin/env python3
from functools import singledispatch

from yachalk import chalk


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
