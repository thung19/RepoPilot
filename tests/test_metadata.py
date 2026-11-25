from repopilot.tools.metadata import find_readme


def test_find_readme(tmp_path):
    readme = tmp_path / "README.md"
    readme.touch()

    assert find_readme(tmp_path) == readme


def test_missing_readme(tmp_path):
    assert find_readme(tmp_path) is None


def test_readme_priority(tmp_path):
    (tmp_path / "README.txt").touch()
    (tmp_path / "README.md").touch()

    assert find_readme(tmp_path).name == "README.md"