"""Structured output the LLM must return.

Every factual item carries `evidence`: repository-relative file paths
that support it. Anything the evidence cannot support belongs in
`unknowns` instead of being guessed. The field descriptions are part of
the prompt, so they are written as instructions to the model.
"""

from pydantic import BaseModel, Field

Evidence = list[str]

EVIDENCE_DESCRIPTION = (
    "Repository-relative file paths, copied exactly from the file "
    "inventory, that directly support this item. Optionally append a "
    "line number as path:line."
)


def evidence_field():
    return Field(min_length=1, description=EVIDENCE_DESCRIPTION)


class Purpose(BaseModel):
    statement: str = Field(
        description="One or two sentences on what the repository does."
    )
    evidence: Evidence = evidence_field()


class Component(BaseModel):
    name: str = Field(
        description="Short name of a module, package, or directory."
    )
    responsibility: str = Field(
        description="What this component is responsible for."
    )
    evidence: Evidence = evidence_field()


class EntryPointSummary(BaseModel):
    path: str = Field(
        description="File path of the entry point, from the inventory."
    )
    description: str = Field(
        description="How this entry point is invoked and what it starts."
    )
    evidence: Evidence = evidence_field()


class DependencySummary(BaseModel):
    name: str = Field(description="Package or tool name.")
    purpose: str = Field(
        description="What the repository uses it for, if evident."
    )
    evidence: Evidence = evidence_field()


class SetupStep(BaseModel):
    instruction: str = Field(
        description="One setup or run step, such as a shell command."
    )
    evidence: Evidence = evidence_field()


class LLMReport(BaseModel):
    purpose: Purpose
    architecture: list[Component] = Field(
        description="Main components and their responsibilities."
    )
    entry_points: list[EntryPointSummary]
    dependencies: list[DependencySummary]
    setup_steps: list[SetupStep] = Field(
        description=(
            "Ordered steps to install and run the project, taken only "
            "from documentation or manifests in the evidence."
        )
    )
    unknowns: list[str] = Field(
        description=(
            "Questions a new developer would ask that the evidence "
            "cannot answer."
        )
    )
