import ast
from pathlib import Path

from repopilot.models import EntryPoint
from repopilot.tools.filesystem import (
    find_files,
    read_file,
)


def is_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False

    test = node.test

    if not isinstance(test, ast.Compare):
        return False

    if len(test.ops) != 1:
        return False

    if len(test.comparators) != 1:
        return False

    return (
        isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and isinstance(test.ops[0], ast.Eq)
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )

def find_python_entrypoints(
    root: Path
) -> list[EntryPoint]:

    results = []

    for path in find_files(root, "*.py"):
        relative_path = path.relative_to(root).as_posix()

        if path.name == "__main__.py":
            results.append(
                EntryPoint(
                    path=relative_path,
                    reason="Python package __main__.py"
                )
            )

        try:
            contents = read_file(root, path)
            tree = ast.parse(contents)

        except (SyntaxError, OSError, UnicodeError, ValueError):
            continue

        for node in tree.body:
            if is_main_guard(node):
                results.append(
                    EntryPoint(
                        path=relative_path,
                        reason="Contains a Python __main__ guard",
                        line_number=node.lineno
                    )
                )

    return results

from repopilot.tools.filesystem import search_code


ENTRYPOINT_RULES = [
    (".py", "FastAPI(", "Possible FastAPI application"),
    (".py", "Flask(", "Possible Flask application"),
    (".java", "public static void main", "Java main method"),
    (".go", "func main(", "Go main function"),
    (".rs", "fn main(", "Rust main function"),
    (".cpp", "int main(", "C++ main function"),
    (".c", "int main(", "C main function"),
]


def find_other_entrypoints(
    root: Path
) -> list[EntryPoint]:

    results = []

    for extension, query, reason in ENTRYPOINT_RULES:
        for match in search_code(root, query):
            if Path(match.file).suffix != extension:
                continue

            results.append(
                EntryPoint(
                    path=match.file,
                    reason=reason,
                    line_number=match.line_number
                )
            )

    return results

def find_entrypoints(root: Path) -> list[EntryPoint]:
    results = (
        find_python_entrypoints(root)
        + find_other_entrypoints(root)
    )

    return sorted(
        results,
        key=lambda entry: (
            entry.path,
            entry.line_number or 0,
            entry.reason
        )
    )