# full-apply

Apply commands to both file contents and paths.

## Installation

```bash
pip3 install full-apply
```

## Usage

```console
$ full-apply --help
Usage: full-apply [OPTIONS] CMD PATHS...

  Apply commands to both file contents and paths.

  File paths and contents will be piped into the given shell command's
  standard input and replaced with its output.

  Examples:

  Replace all occurrences of "foo" with "bar" in both paths and file contents
  within the current directory and sub-directories (will prompt for
  confirmation before actually making any changes):

    $ full-apply -r "sed s/foo/bar/g" .

Arguments:
  CMD       shell command to apply  [required]
  PATHS...  paths to apply to (recursively)  [required]

Options:
  -y, --yes        apply changes without asking (dangerous!)
  -n, --no         don't apply changes and don't even ask
  -H, --hidden     go through "hidden" (dot-prefixed) files
  --binary         go through the contents of binary files
  -r, --recursive  recurse into directories
  --help           Show this message and exit.
```

## Changelog

### 0.7.0

- Now defaults to not going through the contents of binary files.
- Introduced `--binary` option to re-enable the old behavior of doing so.
- Fixed crash on diff output for files with non-UTF-8 contents.
