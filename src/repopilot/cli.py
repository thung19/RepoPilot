import argparse
import sys
from pathlib import Path

from repopilot.pipeline import analyze_repository
from repopilot.reporter import generate_report


def main():

    # Make arg parser
    parser = argparse.ArgumentParser(
        description="RepoPilot: Analyze a local repository"
    )

    # Accept a repo path
    parser.add_argument(
        "repository",
        help="Path to the repository to analyze"
    )

    # Accept optional output argument
    parser.add_argument(
        "--output",
        default="report.md",
        help="Path to the generated report"
    )

    # Parse the args
    args = parser.parse_args()

    # Convert paths into absolute path objects
    repo_path = Path(args.repository).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    # Validate repo path exists and is a directory
    if not repo_path.exists():
        parser.error("Repo path does not exist")

    if not repo_path.is_dir():
        parser.error("Repo path must be a directory")

    # Fail fast before running the analysis. The "x" open mode
    # below is still the real guard against overwriting.
    if output_path.exists():
        sys.exit(f"error: Output file already exists: {output_path}")

    print(f"Inspecting repo: {repo_path}")
    print(f"Output file: {output_path}")

    try:
        analysis = analyze_repository(repo_path)
    except OSError as error:
        sys.exit(f"error: Unable to analyze repository: {error}")

    report = generate_report(analysis)

    try:
        with output_path.open("x", encoding="utf-8") as file:
            file.write(report)

    except FileExistsError:
        sys.exit(f"error: Output file already exists: {output_path}")

    except OSError as error:
        sys.exit(f"error: Unable to write report: {error}")

    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    main()
