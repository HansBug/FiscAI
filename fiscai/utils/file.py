"""
File recovery and management utilities for error handling.

This module provides utilities for managing file operations with automatic
recovery capabilities in case of errors. It ensures data integrity by
maintaining backups during critical file operations and automatically
restoring files to their original state if an error occurs.

The module contains the following main components:

* :func:`file_recovery_on_error` - Context manager for automatic file recovery on errors

.. note::
   This module uses temporary directories for backup storage and automatically
   cleans up resources after operations complete.

.. warning::
   File recovery operations may consume significant disk space for large files.
   Ensure adequate temporary storage is available.

Example::

    >>> from fiscai.utils.file import file_recovery_on_error
    >>> from pathlib import Path
    >>> 
    >>> files_to_protect = ['data.txt', 'config.json']
    >>> 
    >>> with file_recovery_on_error(files_to_protect):
    ...     # Perform risky file operations
    ...     Path('data.txt').write_text('new content')
    ...     Path('config.json').write_text('{"key": "value"}')
    ...     # If an error occurs here, files are automatically restored

"""

import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import List, Union

from hbutils.system import TemporaryDirectory


@contextmanager
def file_recovery_on_error(files: List[Union[str, Path]]):
    """
    Context manager that provides automatic file recovery on error.

    This context manager creates backups of specified files before entering
    the context. If an exception occurs within the context, all files are
    automatically restored to their original state. Files that didn't exist
    before entering the context are deleted if they were created during
    execution.

    The function handles two scenarios for each file:
    
    1. **Existing files**: Creates a backup copy in a temporary directory.
       If an error occurs, the backup is restored to the original location.
    2. **Non-existing files**: Records that the file didn't exist. If an
       error occurs and the file was created during execution, it is deleted.

    :param files: List of file paths to protect with automatic recovery.
                 Paths can be strings or Path objects.
    :type files: List[Union[str, Path]]
    :raises: Re-raises any exception that occurs within the context after
            performing file recovery operations.

    .. note::
       Backups are stored in a temporary directory that is automatically
       cleaned up when the context exits, regardless of success or failure.

    .. warning::
       This function uses :func:`shutil.copy2` which preserves file metadata.
       Large files may take significant time to backup and restore.

    Example::

        >>> from pathlib import Path
        >>> from fiscai.utils.file import file_recovery_on_error
        >>> 
        >>> # Protect existing files during risky operations
        >>> important_files = ['config.json', 'data.db']
        >>> 
        >>> with file_recovery_on_error(important_files):
        ...     # Modify files - if error occurs, they're restored
        ...     Path('config.json').write_text('{"new": "config"}')
        ...     Path('data.db').write_bytes(b'new data')
        ...     # Simulate an error
        ...     raise ValueError("Something went wrong")
        Traceback (most recent call last):
            ...
        ValueError: Something went wrong
        >>> 
        >>> # Files are automatically restored to original state
        >>> 
        >>> # Example with non-existing files
        >>> with file_recovery_on_error(['new_file.txt']):
        ...     Path('new_file.txt').write_text('temporary content')
        ...     raise RuntimeError("Error occurred")
        Traceback (most recent call last):
            ...
        RuntimeError: Error occurred
        >>> 
        >>> # 'new_file.txt' is automatically deleted since it didn't exist before

    Example with successful execution::

        >>> with file_recovery_on_error(['output.txt']):
        ...     Path('output.txt').write_text('success')
        ...     # No error occurs
        >>> 
        >>> # Changes are preserved, backups are cleaned up
        >>> Path('output.txt').read_text()
        'success'

    """
    files = [Path(f) for f in files]

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        backup_info = {}

        # Create backups for existing files and record non-existing files
        for i, file_path in enumerate(files):
            if file_path.exists():
                # Backup existing file with unique name
                backup_file = temp_path / f"backup_{i}_{file_path.name}"
                shutil.copy2(file_path, backup_file)
                backup_info[file_path] = ('exists', backup_file)
            else:
                # Record that file doesn't exist
                backup_info[file_path] = ('not_exists', None)

        try:
            yield
        except:
            # Restore files to original state on error
            for file_path, (status, backup_file) in backup_info.items():
                if status == 'exists':
                    # Restore from backup if backup exists
                    if backup_file and backup_file.exists():
                        shutil.copy2(backup_file, file_path)
                elif status == 'not_exists':
                    # Delete file if it was created during execution
                    if file_path.exists():
                        file_path.unlink()
            raise
