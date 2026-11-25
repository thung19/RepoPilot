from pathlib import Path

from repopilot.tools.filesystem import list_directory


def find_readme(root: Path) -> Path | None:
    candidates = []

    for path in list_directory(root):
        if path.is_file():
            if path.stem.lower() == "readme":
                candidates.append(path)

    if not candidates:
        return None

    preferred_names = [
        "readme.md",
        "readme.rst",
        "readme.txt",
        "readme"
    ]

    for name in preferred_names:
        for path in candidates:
            if path.name.lower() == name:
                return path

    return candidates[0]