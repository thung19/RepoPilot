import argparse
import sys
from pathlib import Path

from repopilot.llm.analyzer import analyze_with_llm
from repopilot.llm.client import (
    DEFAULT_OLLAMA_MODEL,
    LLMError,
    OllamaClient,
)
from repopilot.llm.report import render_llm_report
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

    # V1: interpret the deterministic evidence with an LLM
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Generate an LLM-assisted onboarding guide (V1) via Ollama"
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_OLLAMA_MODEL,
        help=f"Ollama model for --llm (default: {DEFAULT_OLLAMA_MODEL})"
    )

    parser.add_argument(
        "--ollama-host",
        default=None,
        help="Ollama server URL (default: $OLLAMA_HOST or "
             "http://localhost:11434)"
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

    if args.llm:
        client = OllamaClient(model=args.model, host=args.ollama_host)
        print(f"Generating guide with {args.model} (this can take a while)")

        try:
            result = analyze_with_llm(analysis, client)
        except LLMError as error:
            sys.exit(f"error: {error}")

        report = render_llm_report(result)

        if result.issues:
            print(f"Validation issues: {len(result.issues)} (see report)")
    else:
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
