"""Parse and check the LLM's structured output.

Schema validation proves the output has the right shape. The citation
checks below prove only that cited files exist and were shown to the
model; they do not prove that a claim is semantically correct.
"""

import re
from typing import Literal

from pydantic import BaseModel, ValidationError

from repopilot.llm.client import LLMError
from repopilot.llm.evidence import Evidence
from repopilot.llm.schema import LLMReport

IssueKind = Literal[
    "missing_file",
    "unread_file",
    "bad_line",
    "missing_reference",
    "unsupported",
]

LINE_SUFFIX = re.compile(r":(\d+)(?:-(\d+))?$")

# Separators around file names inside a shell command.
COMMAND_SEPARATORS = re.compile(r"[\s=\"'`()<>,;|&]+")

# Tokens that look like a file the command depends on. Dotted module
# names such as repopilot.cli do not match because .cli is not listed.
FILE_TOKEN = re.compile(
    r"[\w./-]*\w\.(?:txt|toml|cfg|ini|json|ya?ml|lock|py|sh|md|rst"
    r"|xml|gradle|mod|kts)"
)


class ValidationIssue(BaseModel):
    location: str
    kind: IssueKind
    message: str


def parse_report(text: str) -> LLMReport:
    try:
        return LLMReport.model_validate_json(text)
    except ValidationError as error:
        raise LLMError(
            f"Model output does not match the report schema:\n{error}"
        ) from error


def normalize_citation(citation: str) -> str:
    path = citation.strip().strip("`").strip()
    path = LINE_SUFFIX.sub("", path)

    if path.startswith("./"):
        path = path[2:]

    return path


def cited_line(citation: str) -> int | None:
    """Highest line number in a path:line or path:start-end citation."""
    match = LINE_SUFFIX.search(citation.strip().strip("`").strip())

    if match is None:
        return None

    return int(match.group(2) or match.group(1))


def referenced_files(instruction: str) -> list[str]:
    """File names mentioned in a setup command, e.g. requirements.txt."""
    files = []

    for token in COMMAND_SEPARATORS.split(instruction):
        if "://" in token:
            continue

        token = token.rstrip(".:")

        if FILE_TOKEN.fullmatch(token):
            files.append(normalize_citation(token))

    return files


def file_exists(reference: str, known_files: set[str]) -> bool:
    """Exact path, or a file with that relative path anywhere.

    Commands often run from a subdirectory, so `cli.py` counts as
    present if any `.../cli.py` exists. Lenient by design: this check
    should catch invented files, not argue about working directories.
    """
    return reference in known_files or any(
        path.endswith("/" + reference) for path in known_files
    )


def cited_items(report: LLMReport):
    """Yield (location, evidence list) for every item with citations."""
    yield "purpose", report.purpose.evidence

    sections = {
        "architecture": report.architecture,
        "entry_points": report.entry_points,
        "dependencies": report.dependencies,
        "setup_steps": report.setup_steps,
    }

    for name, items in sections.items():
        for index, item in enumerate(items):
            yield f"{name}[{index}]", item.evidence


def validate_report(
    report: LLMReport,
    evidence: Evidence,
) -> list[ValidationIssue]:
    known_files = {f.path for f in evidence.analysis.files}
    read_files = {d.path for d in evidence.documents}
    # Line counts are known only for files shown in full.
    line_counts = {
        d.path: len(d.content.splitlines())
        for d in evidence.documents
        if not d.truncated
    }
    issues = []

    for location, citations in cited_items(report):
        valid = 0

        for citation in citations:
            path = normalize_citation(citation)

            if path not in known_files:
                issues.append(ValidationIssue(
                    location=location,
                    kind="missing_file",
                    message=f"Cited file does not exist: {citation}",
                ))
                continue

            line = cited_line(citation)
            line_count = line_counts.get(path)

            if line is not None and line_count is not None:
                if not 1 <= line <= line_count:
                    issues.append(ValidationIssue(
                        location=location,
                        kind="bad_line",
                        message=(
                            f"Cited line {line} is outside {path} "
                            f"({line_count} lines): {citation}"
                        ),
                    ))
                    continue

            valid += 1

            if path not in read_files:
                issues.append(ValidationIssue(
                    location=location,
                    kind="unread_file",
                    message=(
                        f"Cited file was not shown to the model, only "
                        f"its name: {path}"
                    ),
                ))

        if valid == 0:
            issues.append(ValidationIssue(
                location=location,
                kind="unsupported",
                message="No valid evidence supports this item.",
            ))

    for index, entry in enumerate(report.entry_points):
        if normalize_citation(entry.path) not in known_files:
            issues.append(ValidationIssue(
                location=f"entry_points[{index}]",
                kind="missing_file",
                message=f"Entry point file does not exist: {entry.path}",
            ))

    for index, step in enumerate(report.setup_steps):
        for reference in referenced_files(step.instruction):
            if not file_exists(reference, known_files):
                issues.append(ValidationIssue(
                    location=f"setup_steps[{index}]",
                    kind="missing_reference",
                    message=(
                        "Setup step uses a file that does not exist "
                        f"in the repository: {reference}"
                    ),
                ))

    return issues
