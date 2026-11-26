"""Turn a V0 RepositoryAnalysis into bounded context for an LLM.

Evidence collection is deterministic: the same repository always
produces the same evidence text. Repository content is untrusted, so
every file is read through read_file (sandboxed, secrets blocked) and
wrapped in delimiters that the file contents cannot close.
"""

from pathlib import Path

from pydantic import BaseModel, Field

from repopilot.models import RepositoryAnalysis
from repopilot.tools.filesystem import SOURCE_EXTENSIONS, read_file

# Rough guide: 1 token is about 4 characters of English or code.
DEFAULT_MAX_FILE_CHARS = 12_000
DEFAULT_MAX_TOTAL_CHARS = 60_000
DEFAULT_MAX_INVENTORY = 300

FILE_OPEN = '<file path="{path}">'
FILE_CLOSE = "</file>"

# Closing tags used by the evidence and prompt wrappers. File contents
# must not be able to end these blocks early (prompt injection).
RESERVED_CLOSING_TAGS = ("</file>", "</evidence>")


def neutralize(content: str) -> str:
    for tag in RESERVED_CLOSING_TAGS:
        content = content.replace(tag, tag.replace("</", "<\\/"))
    return content


class EvidenceDocument(BaseModel):
    path: str
    content: str
    truncated: bool = False


class Evidence(BaseModel):
    analysis: RepositoryAnalysis
    documents: list[EvidenceDocument] = Field(default_factory=list)
    omitted: list[str] = Field(default_factory=list)


def select_paths(analysis: RepositoryAnalysis) -> list[str]:
    """Files worth reading, most important first, without duplicates."""
    candidates = []

    if analysis.readme_path is not None:
        candidates.append(analysis.readme_path)

    candidates.extend(dep.path for dep in analysis.dependency_files)
    candidates.extend(entry.path for entry in analysis.entry_points)

    # dict.fromkeys keeps the first occurrence and preserves order.
    return list(dict.fromkeys(candidates))


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    return any(
        part in ("test", "tests") or part.startswith("test_")
        for part in parts
    )


def select_source_paths(
    analysis: RepositoryAnalysis,
    exclude: set[str],
) -> list[str]:
    """Source files to fill leftover budget: non-test, shallow first."""
    paths = [
        f.path
        for f in analysis.files
        if f.extension.lower() in SOURCE_EXTENSIONS
        and f.path not in exclude
    ]

    return sorted(
        paths,
        key=lambda p: (is_test_path(p), p.count("/"), p),
    )


def collect_evidence(
    analysis: RepositoryAnalysis,
    max_file_chars: int = DEFAULT_MAX_FILE_CHARS,
    max_total_chars: int = DEFAULT_MAX_TOTAL_CHARS,
) -> Evidence:
    """Read priority files first, then fill leftover budget with source.

    Priority files (README, manifests, entry points) that are skipped
    are each recorded. Skipped filler files are summarized as a count.
    """
    root = Path(analysis.root)
    evidence = Evidence(analysis=analysis)
    remaining = max_total_chars

    def add(relative_path: str, skip_empty: bool) -> None:
        nonlocal remaining

        try:
            content = read_file(root, root / relative_path)
        except (OSError, UnicodeError, ValueError) as error:
            evidence.omitted.append(f"{relative_path}: {error}")
            return

        if skip_empty and not content.strip():
            return

        limit = min(max_file_chars, remaining)
        truncated = len(content) > limit
        content = content[:limit]
        remaining -= len(content)

        evidence.documents.append(
            EvidenceDocument(
                path=relative_path,
                content=content,
                truncated=truncated,
            )
        )

    priority = select_paths(analysis)

    for relative_path in priority:
        if remaining <= 0:
            evidence.omitted.append(
                f"{relative_path}: context budget exhausted"
            )
        else:
            add(relative_path, skip_empty=False)

    skipped = 0

    for relative_path in select_source_paths(analysis, set(priority)):
        if remaining <= 0:
            skipped += 1
        else:
            add(relative_path, skip_empty=True)

    if skipped:
        evidence.omitted.append(
            f"{skipped} more source files: context budget exhausted"
        )

    return evidence


def render_evidence(
    evidence: Evidence,
    max_inventory: int = DEFAULT_MAX_INVENTORY,
) -> str:
    analysis = evidence.analysis
    lines = [
        f"Repository name: {analysis.name}",
        "",
        "## Top-level directories",
    ]
    lines.extend(f"- {d}/" for d in analysis.directories)

    files = analysis.files
    lines.extend(["", f"## File inventory ({len(files)} files)"])
    lines.extend(f"- {f.path}" for f in files[:max_inventory])

    if len(files) > max_inventory:
        lines.append(
            f"- ... {len(files) - max_inventory} more files not listed"
        )

    lines.extend(["", "## Dependency manifests (detected by rules)"])
    lines.extend(
        f"- {dep.path} ({dep.ecosystem})"
        for dep in analysis.dependency_files
    )

    lines.extend(["", "## Candidate entry points (detected by rules)"])
    for entry in analysis.entry_points:
        location = entry.path
        if entry.line_number is not None:
            location += f":{entry.line_number}"
        lines.append(f"- {location}: {entry.reason}")

    if analysis.warnings or evidence.omitted:
        lines.extend(["", "## Collection notes"])
        lines.extend(f"- {w}" for w in analysis.warnings)
        lines.extend(f"- Not included: {o}" for o in evidence.omitted)

    lines.extend(["", "## File contents"])
    for doc in evidence.documents:
        lines.append(FILE_OPEN.format(path=doc.path))
        lines.append(neutralize(doc.content))
        if doc.truncated:
            lines.append("[... truncated ...]")
        lines.append(FILE_CLOSE)

    return "\n".join(lines) + "\n"
