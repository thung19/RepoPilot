from repopilot.tools.entrypoints import (
    find_other_entrypoints,
    find_python_entrypoints,
)


def test_python_entrypoint(tmp_path):
    path = tmp_path / "main.py"

    path.write_text(
        'if __name__ == "__main__":\n'
        '    print("hello")\n'
    )

    results = find_python_entrypoints(tmp_path)

    assert len(results) == 1
    assert results[0].path == "main.py"
    assert results[0].line_number == 1


def test_no_entrypoint(tmp_path):
    path = tmp_path / "utils.py"
    path.write_text("def helper():\n    pass\n")

    assert find_python_entrypoints(tmp_path) == []


def test_commented_entrypoint(tmp_path):
    path = tmp_path / "main.py"

    path.write_text(
        '# if __name__ == "__main__":\n'
    )

    assert find_python_entrypoints(tmp_path) == []


def test_invalid_syntax(tmp_path):
    path = tmp_path / "broken.py"
    path.write_text("def broken(")

    assert find_python_entrypoints(tmp_path) == []

def test_other_entrypoint(tmp_path):
    (tmp_path / "main.go").write_text(
        "package main\n"
        "func main() {}\n"
    )

    results = find_other_entrypoints(tmp_path)

    assert len(results) == 1
    assert results[0].path == "main.go"
    assert results[0].line_number == 2
    assert results[0].reason == "Go main function"
