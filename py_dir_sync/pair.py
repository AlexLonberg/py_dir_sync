import pathlib

from .utils import validate_path_pair


class SyncPathPair:
    def __init__(self, src_abs_dir_path: pathlib.Path, dest_abs_dir_path: pathlib.Path):
        self._src, self._dest = validate_path_pair(src_abs_dir_path, dest_abs_dir_path)

    @property
    def src(self) -> pathlib.Path:
        return self._src

    @property
    def dest(self) -> pathlib.Path:
        return self._dest
