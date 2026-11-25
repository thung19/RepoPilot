from repopilot.tools.dependencies import find_dependency_files


def test_find_dependencies(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "package.json").touch()

    results = find_dependency_files(tmp_path)

    ecosystems = {result.ecosystem for result in results}

    assert ecosystems == {"Python", "Node.js"}


def test_nested_dependencies(tmp_path):
    backend = tmp_path / "backend"
    backend.mkdir()

    (backend / "requirements.txt").touch()

    results = find_dependency_files(tmp_path)

    assert len(results) == 1
    assert results[0].path == "backend/requirements.txt"