import pytest

from app.tools.files import FileReaderArgs, handle


def test_reads_file_in_sandbox():
    result = handle(FileReaderArgs(path="welcome.txt"))
    assert "sandbox" in result["content"].lower()
    assert result["truncated"] is False


def test_missing_file_raises():
    with pytest.raises(ValueError):
        handle(FileReaderArgs(path="does-not-exist.txt"))


def test_path_traversal_is_blocked():
    with pytest.raises(ValueError):
        handle(FileReaderArgs(path="../requirements.txt"))


def test_absolute_path_escape_is_blocked():
    with pytest.raises(ValueError):
        handle(FileReaderArgs(path="/etc/passwd"))
