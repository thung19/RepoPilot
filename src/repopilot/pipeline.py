from pathlib import Path

from repopilot.models import (
    RepositoryAnalysis,
    FileInfo,
)

from repopilot.tools.filesystem import (
    list_directory,
    find_files,
    read_file,
)

from repopilot.tools.metadata import find_readme
from repopilot.tools.dependencies import find_dependency_files
from repopilot.tools.entrypoints import find_entrypoints

def analyze_repository(root: Path) -> RepositoryAnalysis:
    root = root.resolve()

    if not root.exists():
        raise FileNotFoundError(root)

    if not root.is_dir():
        raise NotADirectoryError(root)

    # 1. Initialize analysis state
    analysis = RepositoryAnalysis(
        name=root.name,
        root=str(root)
    )

    # 2. Discover top-level directories
    analysis.directories = [
        path.relative_to(root).as_posix()
        for path in list_directory(root)
        if path.is_dir()
    ]

    # 3. Discover repository files
    for path in find_files(root, "*"):
        analysis.files.append(
            FileInfo(
                path=path.relative_to(root).as_posix(),
                name=path.name,
                extension=path.suffix
            )
        )

    # 4. Find and read README
    readme = find_readme(root)

    if readme is not None:
        analysis.readme_path = readme.relative_to(root).as_posix()

        try:
            analysis.readme_content = read_file(root, readme)

        except (OSError, UnicodeError, ValueError) as error:
            analysis.warnings.append(
                f"Unable to read README: {error}"
            )
    else:
        analysis.warnings.append("No root README found")

    # 5. Find dependency manifests
    analysis.dependency_files = find_dependency_files(root)

    # 6. Identify candidate entry points
    analysis.entry_points = find_entrypoints(root)

    # 7. Return completed analysis
    return analysis