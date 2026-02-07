"""
Unit tests for fiscai.utils.file module.

This module contains comprehensive tests for the file_recovery_on_error context manager,
which provides automatic file backup and recovery on error.
"""

import tempfile
from pathlib import Path

import pytest

from fiscai.utils.file import file_recovery_on_error


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_files(temp_dir):
    """Create test files with initial content."""
    files = []
    for i in range(3):
        file_path = temp_dir / f"test_file_{i}.txt"
        file_path.write_text(f"Initial content {i}")
        files.append(file_path)
    return files


@pytest.fixture
def non_existent_files(temp_dir):
    """Create paths for non-existent files."""
    return [temp_dir / f"non_existent_{i}.txt" for i in range(3)]


@pytest.mark.unittest
class TestFileRecoveryOnErrorBasic:
    """Basic tests for file_recovery_on_error context manager."""

    def test_no_error_existing_files_unchanged(self, test_files):
        """Test that existing files remain unchanged when no error occurs."""
        original_contents = [f.read_text() for f in test_files]

        with file_recovery_on_error(test_files):
            # Modify files
            for i, f in enumerate(test_files):
                f.write_text(f"Modified content {i}")

        # Files should keep modified content (no recovery)
        for i, f in enumerate(test_files):
            assert f.read_text() == f"Modified content {i}"
            assert f.exists()

    def test_no_error_non_existent_files_remain(self, non_existent_files):
        """Test that non-existent files remain non-existent when no error occurs."""
        with file_recovery_on_error(non_existent_files):
            # Create some files
            for i, f in enumerate(non_existent_files[:2]):
                f.write_text(f"New content {i}")

        # Created files should still exist (no recovery)
        assert non_existent_files[0].exists()
        assert non_existent_files[1].exists()
        assert not non_existent_files[2].exists()

    def test_error_existing_files_recovered(self, test_files):
        """Test that existing files are recovered to original state on error."""
        original_contents = [f.read_text() for f in test_files]

        with pytest.raises(ValueError):
            with file_recovery_on_error(test_files):
                # Modify files
                for i, f in enumerate(test_files):
                    f.write_text(f"Modified content {i}")
                raise ValueError("Test error")

        # Files should be recovered to original content
        for i, f in enumerate(test_files):
            assert f.read_text() == original_contents[i]
            assert f.exists()

    def test_error_non_existent_files_removed(self, non_existent_files):
        """Test that files created during error are removed on recovery."""
        with pytest.raises(RuntimeError):
            with file_recovery_on_error(non_existent_files):
                # Create files
                for i, f in enumerate(non_existent_files):
                    f.write_text(f"New content {i}")
                raise RuntimeError("Test error")

        # All files should be removed (recovered to non-existent state)
        for f in non_existent_files:
            assert not f.exists()

    def test_mixed_existing_and_non_existent_files(self, temp_dir):
        """Test recovery with mixed existing and non-existent files."""
        existing_file = temp_dir / "existing.txt"
        existing_file.write_text("Original content")
        non_existent_file = temp_dir / "non_existent.txt"

        files = [existing_file, non_existent_file]

        with pytest.raises(Exception):
            with file_recovery_on_error(files):
                existing_file.write_text("Modified content")
                non_existent_file.write_text("New content")
                raise Exception("Test error")

        # Existing file should be recovered
        assert existing_file.read_text() == "Original content"
        # Non-existent file should be removed
        assert not non_existent_file.exists()


@pytest.mark.unittest
class TestFileRecoveryOnErrorEdgeCases:
    """Edge case tests for file_recovery_on_error context manager."""

    def test_empty_file_list(self):
        """Test with empty file list."""
        with file_recovery_on_error([]):
            pass  # Should not raise any error

    def test_empty_file_list_with_error(self):
        """Test with empty file list when error occurs."""
        with pytest.raises(ValueError):
            with file_recovery_on_error([]):
                raise ValueError("Test error")

    def test_single_file(self, temp_dir):
        """Test with single file."""
        single_file = temp_dir / "single.txt"
        single_file.write_text("Original")

        with pytest.raises(Exception):
            with file_recovery_on_error([single_file]):
                single_file.write_text("Modified")
                raise Exception("Error")

        assert single_file.read_text() == "Original"

    def test_string_paths(self, temp_dir):
        """Test that string paths are handled correctly."""
        file_path = temp_dir / "string_path.txt"
        file_path.write_text("Original")

        with pytest.raises(Exception):
            with file_recovery_on_error([str(file_path)]):
                file_path.write_text("Modified")
                raise Exception("Error")

        assert file_path.read_text() == "Original"

    def test_path_objects(self, temp_dir):
        """Test that Path objects are handled correctly."""
        file_path = temp_dir / "path_object.txt"
        file_path.write_text("Original")

        with pytest.raises(Exception):
            with file_recovery_on_error([file_path]):
                file_path.write_text("Modified")
                raise Exception("Error")

        assert file_path.read_text() == "Original"

    def test_mixed_string_and_path(self, temp_dir):
        """Test with mixed string and Path objects."""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        file1.write_text("Content1")
        file2.write_text("Content2")

        with pytest.raises(Exception):
            with file_recovery_on_error([str(file1), file2]):
                file1.write_text("Modified1")
                file2.write_text("Modified2")
                raise Exception("Error")

        assert file1.read_text() == "Content1"
        assert file2.read_text() == "Content2"


@pytest.mark.unittest
class TestFileRecoveryOnErrorFileOperations:
    """Tests for various file operations during recovery."""

    def test_file_deletion_recovery(self, test_files):
        """Test that deleted files are recovered."""
        original_contents = [f.read_text() for f in test_files]

        with pytest.raises(Exception):
            with file_recovery_on_error(test_files):
                # Delete files
                for f in test_files:
                    f.unlink()
                raise Exception("Error")

        # Files should be recovered
        for i, f in enumerate(test_files):
            assert f.exists()
            assert f.read_text() == original_contents[i]

    def test_file_metadata_preservation(self, temp_dir):
        """Test that file metadata is preserved during recovery."""
        test_file = temp_dir / "metadata_test.txt"
        test_file.write_text("Original content")

        # Get original metadata
        original_stat = test_file.stat()

        with pytest.raises(Exception):
            with file_recovery_on_error([test_file]):
                test_file.write_text("Modified content")
                raise Exception("Error")

        # Content should be recovered
        assert test_file.read_text() == "Original content"
        # Metadata should be preserved (mtime, atime)
        recovered_stat = test_file.stat()
        assert abs(recovered_stat.st_mtime - original_stat.st_mtime) < 0.1

    def test_multiple_modifications(self, test_files):
        """Test recovery after multiple modifications."""
        original_contents = [f.read_text() for f in test_files]

        with pytest.raises(Exception):
            with file_recovery_on_error(test_files):
                # Multiple modifications
                for f in test_files:
                    f.write_text("First modification")
                for f in test_files:
                    f.write_text("Second modification")
                for f in test_files:
                    f.write_text("Third modification")
                raise Exception("Error")

        # Files should be recovered to original state
        for i, f in enumerate(test_files):
            assert f.read_text() == original_contents[i]

    def test_partial_file_creation(self, temp_dir):
        """Test recovery when only some files are created."""
        files = [temp_dir / f"partial_{i}.txt" for i in range(5)]

        with pytest.raises(Exception):
            with file_recovery_on_error(files):
                # Create only first 3 files
                for f in files[:3]:
                    f.write_text("Content")
                raise Exception("Error")

        # All files should be non-existent after recovery
        for f in files:
            assert not f.exists()


@pytest.mark.unittest
class TestFileRecoveryOnErrorExceptionHandling:
    """Tests for exception handling in file_recovery_on_error."""

    @pytest.mark.parametrize("exception_type,exception_msg", [
        (ValueError, "Value error occurred"),
        (RuntimeError, "Runtime error occurred"),
        (IOError, "IO error occurred"),
        (KeyError, "Key error occurred"),
        (TypeError, "Type error occurred"),
    ])
    def test_various_exception_types(self, test_files, exception_type, exception_msg):
        """Test that various exception types trigger recovery."""
        original_contents = [f.read_text() for f in test_files]

        with pytest.raises(exception_type, match=exception_msg):
            with file_recovery_on_error(test_files):
                for f in test_files:
                    f.write_text("Modified")
                raise exception_type(exception_msg)

        # Files should be recovered
        for i, f in enumerate(test_files):
            assert f.read_text() == original_contents[i]

    def test_nested_context_managers(self, temp_dir):
        """Test nested file_recovery_on_error context managers."""
        outer_file = temp_dir / "outer.txt"
        inner_file = temp_dir / "inner.txt"
        outer_file.write_text("Outer original")
        inner_file.write_text("Inner original")

        with pytest.raises(Exception):
            with file_recovery_on_error([outer_file]):
                outer_file.write_text("Outer modified")

                with pytest.raises(Exception):
                    with file_recovery_on_error([inner_file]):
                        inner_file.write_text("Inner modified")
                        raise Exception("Inner error")

                # Inner file should be recovered at this point
                assert inner_file.read_text() == "Inner original"
                raise Exception("Outer error")

        # Both files should be recovered
        assert outer_file.read_text() == "Outer original"
        assert inner_file.read_text() == "Inner original"

    def test_exception_during_recovery(self, temp_dir, monkeypatch):
        """Test behavior when exception occurs during recovery process."""
        test_file = temp_dir / "recovery_error.txt"
        test_file.write_text("Original")

        # This test verifies that the original exception is re-raised
        # even if recovery operations encounter issues
        with pytest.raises(ValueError):
            with file_recovery_on_error([test_file]):
                test_file.write_text("Modified")
                raise ValueError("Original error")


@pytest.mark.unittest
class TestFileRecoveryOnErrorComplexScenarios:
    """Complex scenario tests for file_recovery_on_error."""

    def test_large_number_of_files(self, temp_dir):
        """Test with a large number of files."""
        num_files = 100
        files = []
        for i in range(num_files):
            f = temp_dir / f"large_test_{i}.txt"
            f.write_text(f"Content {i}")
            files.append(f)

        with pytest.raises(Exception):
            with file_recovery_on_error(files):
                for i, f in enumerate(files):
                    f.write_text(f"Modified {i}")
                raise Exception("Error")

        # All files should be recovered
        for i, f in enumerate(files):
            assert f.read_text() == f"Content {i}"

    def test_file_with_special_characters(self, temp_dir):
        """Test with files having special characters in names."""
        special_names = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.multiple.dots.txt",
        ]
        files = [temp_dir / name for name in special_names]

        for f in files:
            f.write_text("Original")

        with pytest.raises(Exception):
            with file_recovery_on_error(files):
                for f in files:
                    f.write_text("Modified")
                raise Exception("Error")

        for f in files:
            assert f.read_text() == "Original"

    def test_binary_file_recovery(self, temp_dir):
        """Test recovery of binary files."""
        binary_file = temp_dir / "binary.bin"
        original_data = bytes([i % 256 for i in range(1000)])
        binary_file.write_bytes(original_data)

        with pytest.raises(Exception):
            with file_recovery_on_error([binary_file]):
                binary_file.write_bytes(b"Modified binary data")
                raise Exception("Error")

        assert binary_file.read_bytes() == original_data

    def test_concurrent_file_modifications(self, temp_dir):
        """Test recovery with interleaved file modifications."""
        files = [temp_dir / f"concurrent_{i}.txt" for i in range(5)]
        for f in files:
            f.write_text("Original")

        with pytest.raises(Exception):
            with file_recovery_on_error(files):
                # Interleaved modifications
                files[0].write_text("Mod1")
                files[2].write_text("Mod2")
                files[1].write_text("Mod3")
                files[4].write_text("Mod4")
                files[3].write_text("Mod5")
                raise Exception("Error")

        for f in files:
            assert f.read_text() == "Original"

    def test_empty_file_recovery(self, temp_dir):
        """Test recovery of empty files."""
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")

        with pytest.raises(Exception):
            with file_recovery_on_error([empty_file]):
                empty_file.write_text("Now has content")
                raise Exception("Error")

        assert empty_file.read_text() == ""
        assert empty_file.exists()
