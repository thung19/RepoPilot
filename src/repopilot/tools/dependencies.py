from pathlib import Path

from repopilot.models import DependencyFile
from repopilot.tools.filesystem import find_files


DEPENDENCY_MANIFESTS = {
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "Pipfile": "Python",
    "setup.py": "Python",
    "setup.cfg": "Python",
    "package.json": "Node.js",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java",
    "build.gradle": "Java/JVM",
    "build.gradle.kts": "JVM",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "CMakeLists.txt": "C/C++",
}


def find_dependency_files(
    root: Path
) -> list[DependencyFile]:

    results = []

    for path in find_files(root, "*"):
        if path.name in DEPENDENCY_MANIFESTS:
            results.append(
                DependencyFile(
                    path=path.relative_to(root).as_posix(),
                    ecosystem=DEPENDENCY_MANIFESTS[path.name]
                )
            )

    return results