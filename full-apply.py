#!/usr/bin/env python3
from difflib import diff_bytes, unified_diff
from pathlib import Path
from subprocess import CalledProcessError, run
from sys import argv, stderr, stdout

cmd = argv[1]
path = argv[2]


def run_replace_cmd(buf: bytes) -> bytes:
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
    return r.stdout


def apply_to_path_and_content(path: Path):
    # apply to path
    path_str = str(path)
    new_path_str = run_replace_cmd(path_str.encode("utf-8")).decode("utf-8")
    if new_path_str != path_str:
        print(f"p: {path_str} -> {new_path_str}")
        if argv[3:] == ["--yes"]:
            Path.rename(new_path_str)
    if path.is_file():
        # apply to contents
        content_bytes = path.read_bytes()
        new_content_bytes = run_replace_cmd(content_bytes)
        content_diff = diff_bytes(
            unified_diff,
            content_bytes.splitlines(keepends=True),
            new_content_bytes.splitlines(keepends=True),
            fromfile=b"old",
            tofile=b"new",
        )
        if new_content_bytes != content_bytes:
            print(f"c: {path_str}")
            for diff_line in content_diff:
                stdout.buffer.write(b"     " + diff_line)
            if argv[3:] == ["--yes"]:
                path.write_bytes(new_content_bytes)


def apply_recur(path: Path):
    apply_to_path_and_content(path)
    if path.is_dir():
        for subpath in path.iterdir():
            apply_recur(subpath)


if __name__ == "__main__":
    apply_recur(Path(path))
