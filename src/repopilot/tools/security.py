from pathlib import Path


def validate_path(root: Path, path: Path) -> Path:
    root = root.resolve()
    path = path.resolve()

    if not path.is_relative_to(root):
        raise PermissionError(
            f"Access outside repository: {path}"
        )

    return path