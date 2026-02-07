import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import List, Union

from hbutils.system import TemporaryDirectory


@contextmanager
def file_recovery_on_error(files: List[Union[str, Path]]):
    files = [Path(f) for f in files]

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        backup_info = {}

        for i, file_path in enumerate(files):
            if file_path.exists():
                backup_file = temp_path / f"backup_{i}_{file_path.name}"
                shutil.copy2(file_path, backup_file)
                backup_info[file_path] = ('exists', backup_file)
            else:
                backup_info[file_path] = ('not_exists', None)

        try:
            yield
        except:
            for file_path, (status, backup_file) in backup_info.items():
                if status == 'exists':
                    if backup_file and backup_file.exists():
                        shutil.copy2(backup_file, file_path)
                elif status == 'not_exists':
                    if file_path.exists():
                        file_path.unlink()
            raise
