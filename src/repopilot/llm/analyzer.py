"""V1 pipeline: deterministic evidence -> one LLM call -> validation.

The LLM never chooses what to inspect; it only interprets the evidence
collected by the V0 pipeline.
"""

from pydantic import BaseModel

from repopilot.llm.client import LLMClient, LLMError, LLMResponse
from repopilot.llm.evidence import (
    DEFAULT_MAX_TOTAL_CHARS,
    Evidence,
    collect_evidence,
    render_evidence,
)
from repopilot.llm.prompt import build_system_prompt, build_user_prompt
from repopilot.llm.schema import LLMReport
from repopilot.llm.validation import (
    ValidationIssue,
    parse_report,
    validate_report,
)
from repopilot.models import RepositoryAnalysis


class LLMAnalysis(BaseModel):
    report: LLMReport
    issues: list[ValidationIssue]
    response: LLMResponse
    evidence: Evidence


MAX_FIT_ATTEMPTS = 5


def fit_evidence(
    analysis: RepositoryAnalysis,
    system: str,
    max_prompt_chars: int,
    max_evidence_chars: int,
) -> tuple[Evidence, str]:
    """Shrink the file-content budget until the whole prompt fits.

    The inventory, rule findings, and instructions are not part of the
    file-content budget, so the prompt is measured after rendering and
    the budget is reduced by the overflow. Deterministic for a given
    repository and client.
    """
    budget = max_evidence_chars

    for _ in range(MAX_FIT_ATTEMPTS):
        evidence = collect_evidence(analysis, max_total_chars=budget)
        user = build_user_prompt(render_evidence(evidence))
        overflow = len(system) + len(user) - max_prompt_chars

        if overflow <= 0:
            return evidence, user

        # Shrink from what was actually used: the nominal budget may be
        # far larger than the repository's content.
        used = sum(len(d.content) for d in evidence.documents)
        budget = used - overflow

        if budget <= 0:
            break

    raise LLMError(
        "Repository metadata alone does not fit in the model's context "
        f"({max_prompt_chars} prompt characters). Use a model with a "
        "larger context window."
    )


def analyze_with_llm(
    analysis: RepositoryAnalysis,
    client: LLMClient,
    max_evidence_chars: int = DEFAULT_MAX_TOTAL_CHARS,
) -> LLMAnalysis:
    schema = LLMReport.model_json_schema()
    system = build_system_prompt(schema)

    evidence, user = fit_evidence(
        analysis, system, client.max_prompt_chars, max_evidence_chars
    )

    response = client.generate(system=system, user=user, schema=schema)

    report = parse_report(response.text)

    return LLMAnalysis(
        report=report,
        issues=validate_report(report, evidence),
        response=response,
        evidence=evidence,
    )
