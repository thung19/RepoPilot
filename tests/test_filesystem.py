import pytest

from repopilot.models import SearchResult
from repopilot.tools.filesystem import (
    list_directory,
    read_file,
    find_files,
    search_code,
)


def test_list_directory(tmp_path):
    (tmp_path / "main.py").touch()
    (tmp_path / "README.md").touch()
    (tmp_path / ".git").mkdir()

    result = list_directory(tmp_path)

    assert [p.name for p in result] == [
        "README.md",
        "main.py"
    ]


def test_read_file(tmp_path):
    path = tmp_path / "main.py"
    path.write_text("print('hello')")

    assert read_file(tmp_path, path) == "print('hello')"


def test_read_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_file(tmp_path, tmp_path / "missing.py")


def test_find_files(tmp_path):
    src = tmp_path / "src"
    src.mkdir()

    (src / "main.py").touch()
    (src / "utils.py").touch()
    (src / "README.md").touch()

    result = find_files(tmp_path, "*.py")

    assert [p.name for p in result] == [
        "main.py",
        "utils.py"
    ]


def test_find_files_ignored(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()

    (venv / "package.py").touch()
    (tmp_path / "main.py").touch()

    result = find_files(tmp_path, "*.py")

    assert len(result) == 1
    assert result[0].name == "main.py"


def test_search_code(tmp_path):
    path = tmp_path / "main.py"

    path.write_text(
        "import os\n"
        "def main():\n"
        "    pass\n"
    )

    result = search_code(tmp_path, "def main")

    assert result == [
        SearchResult(
            file="main.py",
            line_number=2,
            content="def main():"
        )
    ]


def test_read_file_rejects_symlink(tmp_path):
    target = tmp_path / "main.py"
    target.write_text("x")
    link = tmp_path / "link.py"
    link.symlink_to(target)

    with pytest.raises(PermissionError):
        read_file(tmp_path, link)


def test_read_file_rejects_broken_symlink(tmp_path):
    link = tmp_path / "link.py"
    link.symlink_to(tmp_path / "missing.py")

    with pytest.raises(PermissionError):
        read_file(tmp_path, link)


def test_list_directory_not_a_directory(tmp_path):
    path = tmp_path / "main.py"
    path.touch()

    with pytest.raises(NotADirectoryError):
        list_directory(path)


def test_find_files_skips_symlinked_dirs(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "a.py").touch()
    (tmp_path / "linked").symlink_to(real, target_is_directory=True)

    result = find_files(tmp_path, "*.py")

    assert [p.relative_to(tmp_path).as_posix() for p in result] == [
        "real/a.py"
    ]


def test_search_code_empty_query(tmp_path):
    with pytest.raises(ValueError):
        search_code(tmp_path, "")


def test_search_code_skips_non_source_files(tmp_path):
    (tmp_path / "notes.md").write_text("def main")

    assert search_code(tmp_path, "def main") == []


def test_search_code_nested_path(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("def main():\n")

    result = search_code(tmp_path, "def main")

    assert result == [
        SearchResult(
            file="src/app.py",
            line_number=1,
            content="def main():"
        )
    ]

def test_read_file_rejects_outside_root(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "secret.py"
    outside.write_text("x")

    with pytest.raises(PermissionError):
        read_file(root, outside)


def test_read_file_rejects_env(tmp_path):
    path = tmp_path / ".env"
    path.write_text("SECRET=1")

    with pytest.raises(PermissionError):
        read_file(tmp_path, path)
