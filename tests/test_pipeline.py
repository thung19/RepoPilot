from repopilot.pipeline import analyze_repository


def test_analyze_repository(tmp_path):
    # Create a simulated repository
    src = tmp_path / "src"
    src.mkdir()

    (tmp_path / "README.md").write_text(
        "# Example Project"
    )

    (tmp_path / "requirements.txt").write_text(
        "fastapi\n"
    )

    (src / "main.py").write_text(
        'if __name__ == "__main__":\n'
        '    print("hello")\n'
    )

    # Execute entire pipeline
    analysis = analyze_repository(tmp_path)

    # Validate results
    assert analysis.name == tmp_path.name
    assert analysis.directories == ["src"]

    assert len(analysis.files) == 3

    assert analysis.readme_path == "README.md"
    assert analysis.readme_content == "# Example Project"

    assert len(analysis.dependency_files) == 1
    assert analysis.dependency_files[0].ecosystem == "Python"

    assert len(analysis.entry_points) == 1
    assert analysis.entry_points[0].path == "src/main.py"

    assert analysis.warnings == []

def test_empty_repository(tmp_path):
    analysis = analyze_repository(tmp_path)

    assert analysis.files == []
    assert analysis.directories == []
    assert analysis.entry_points == []
    assert analysis.dependency_files == []
    assert analysis.readme_path is None

    assert "No root README found" in analysis.warnings