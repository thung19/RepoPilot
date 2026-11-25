import pytest
from pydantic import ValidationError

from repopilot.models import (
    RepositoryAnalysis,
    FileInfo,
    SearchResult,
)


def test_repository_analysis():
    analysis = RepositoryAnalysis(
        name="example",
        root="/projects/example"
    )

    assert analysis.files == []
    assert analysis.entry_points == []


def test_add_file():
    analysis = RepositoryAnalysis(
        name="example",
        root="/projects/example"
    )

    analysis.files.append(
        FileInfo(
            path="main.py",
            name="main.py",
            extension=".py"
        )
    )

    assert len(analysis.files) == 1
    assert analysis.files[0].name == "main.py"


def test_invalid_line_number():
    with pytest.raises(ValidationError):
        SearchResult(
            file="main.py",
            line_number=0,
            content="hello"
        )


def test_independent_lists():
    first = RepositoryAnalysis(name="first", root="/first")
    second = RepositoryAnalysis(name="second", root="/second")

    first.directories.append("src")

    assert second.directories == []