import fnmatch
import os
from pathlib import Path

from repopilot.models import SearchResult
from repopilot.tools.security import validate_path

SOURCE_EXTENSIONS = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".scala",
    ".sh",
}

IGNORED_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".DS_Store",
    "dist",
    "build",
}

# Generated directories whose names vary, matched by suffix.
IGNORED_SUFFIXES = (
    ".egg-info",
)


def is_ignored(name: str) -> bool:
    return name in IGNORED_NAMES or name.endswith(IGNORED_SUFFIXES)

def list_directory(path: Path) -> list[Path]:
    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_dir():
        raise NotADirectoryError(path)

    items = []
    for item in path.iterdir():
        if not is_ignored(item.name) and not item.is_symlink():
            items.append(item)

    return sorted(items)


def read_file(root: Path, path: Path) -> str:
    if path.is_symlink():
        raise PermissionError("Symbolic links are not supported")

    path = validate_path(root, path)

    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_file():
        raise ValueError("Path must be a regular file")

    if path.name == ".env" or path.name.startswith(".env."):
        raise PermissionError("Sensitive file")

    if path.suffix.lower() in {".pem", ".key", ".p12"}:
        raise PermissionError("Potential private key file")

    if path.stat().st_size > 1_000_000:
        raise ValueError("File exceeds maximum size")

    return path.read_text(encoding="utf-8")


def find_files(root: Path, pattern: str) -> list[Path]:
    """Recursively find files whose name (not path) matches `pattern`."""
    if not root.exists():
        raise FileNotFoundError(root)

    if not root.is_dir():
        raise NotADirectoryError(root)

    results = []

    for dirpath, dirnames, filenames in os.walk(root):
        filtered_dirs = []

        for name in dirnames:
            if is_ignored(name):
                continue

            full_path = Path(dirpath) / name

            if full_path.is_symlink():
                continue

            filtered_dirs.append(name)

        dirnames[:] = filtered_dirs

        for filename in filenames:
            if is_ignored(filename):
                continue

            path = Path(dirpath) / filename

            if path.is_symlink():
                continue

            if fnmatch.fnmatchcase(filename, pattern):
                results.append(path)

    return sorted(results)

def search_code(root: Path, query: str) -> list[SearchResult]:
    if not query:
        raise ValueError("Search query cannot be empty")

    results = []

    for path in find_files(root, "*"):
        if path.suffix not in SOURCE_EXTENSIONS:
            continue

        try:
            contents = read_file(root, path)
        except (OSError, UnicodeError, ValueError):
            continue

        for line_number, line in enumerate(
            contents.splitlines(), start=1
        ):
            if query in line:
                results.append(
                    SearchResult(
                        file=path.relative_to(root).as_posix(),
                        line_number=line_number,
                        content=line.strip()
                    )
                )

    return results