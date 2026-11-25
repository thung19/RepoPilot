import pytest

from repopilot.tools.security import validate_path


def test_allowed_path(tmp_path):
    path = tmp_path / "main.py"

    assert validate_path(tmp_path, path) == path.resolve()


def test_outside_repository(tmp_path):
    outside = tmp_path.parent / "secret.txt"

    with pytest.raises(PermissionError):
        validate_path(tmp_path, outside)