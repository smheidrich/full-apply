from abc import ABC, abstractmethod
from pathlib import Path


class Change(ABC):
    replace_cmd_stderr: bytes

    @abstractmethod
    def apply_to_fs(self):
        ...


class PathChange(Change):
    def __init__(
        self,
        old: Path,
        new: Path,
        dest_exists: bool,
        old_is_dir: bool,
        replace_cmd_stderr: bytes,
    ):
        self.old = old
        self.new = new
        self.dest_exists = dest_exists
        self.old_is_dir = old_is_dir
        self.replace_cmd_stderr = replace_cmd_stderr

    def apply_to_fs(self, overwrite: bool = False):
        if self.old_is_dir or self.old.is_dir():
            print("directories not supported yet, skipping...")
            return
        # TODO use atomic rename-if-not-exists function instead to be safe
        if (self.dest_exists and overwrite) or not self.new.exists():
            print(f"moving {self.old} → {self.new}")
            self.new.parent.mkdir(exist_ok=True, parents=True)
            self.old.rename(self.new)
        else:
            msg = "file already exists"
            if not overwrite:
                msg += f" and {overwrite=}"
            elif not self.dest_exists:
                msg += ", unexpectedly"
            raise RuntimeError(msg)


class ContentChange(Change):
    def __init__(
        self, path: Path, old: bytes, new: bytes, replace_cmd_stderr: bytes
    ):
        self.path = path
        self.old = old
        self.new = new
        self.replace_cmd_stderr = replace_cmd_stderr

    def apply_to_fs(self):
        print(f"writing to {self.path}")
        self.path.write_bytes(self.new)
