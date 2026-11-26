import json

import pytest

from llm_fakes import make_repo, report_dict
from repopilot.llm.client import LLMError
from repopilot.llm.evidence import collect_evidence
from repopilot.llm.validation import (
    cited_line,
    normalize_citation,
    parse_report,
    referenced_files,
    validate_report,
)
from repopilot.pipeline import analyze_repository


def evidence_for(tmp_path):
    return collect_evidence(analyze_repository(make_repo(tmp_path)))


def kinds(issues):
    return [(i.location, i.kind) for i in issues]


@pytest.mark.parametrize("raw, expected", [
    ("app.py", "app.py"),
    ("./app.py", "app.py"),
    ("app.py:12", "app.py"),
    ("app.py:3-9", "app.py"),
    (" `src/app.py` ", "src/app.py"),
])
def test_normalize_citation(raw, expected):
    assert normalize_citation(raw) == expected


def test_parse_valid_report():
    report = parse_report(json.dumps(report_dict()))

    assert report.purpose.statement == "A small Flask web app."


def test_parse_rejects_invalid_json():
    with pytest.raises(LLMError, match="does not match"):
        parse_report("{not json")


def test_parse_rejects_missing_evidence():
    data = report_dict()
    data["architecture"][0]["evidence"] = []

    with pytest.raises(LLMError):
        parse_report(json.dumps(data))


def test_valid_report_has_no_issues(tmp_path):
    report = parse_report(json.dumps(report_dict()))

    assert validate_report(report, evidence_for(tmp_path)) == []


def test_hallucinated_citation(tmp_path):
    data = report_dict()
    data["architecture"][0]["evidence"] = ["app.py", "server.py"]
    report = parse_report(json.dumps(data))

    issues = validate_report(report, evidence_for(tmp_path))

    # One bad citation, but a valid one remains: not unsupported.
    assert kinds(issues) == [("architecture[0]", "missing_file")]


def test_all_citations_invalid_is_unsupported(tmp_path):
    data = report_dict()
    data["dependencies"][0]["evidence"] = ["Pipfile"]
    report = parse_report(json.dumps(data))

    issues = validate_report(report, evidence_for(tmp_path))

    assert kinds(issues) == [
        ("dependencies[0]", "missing_file"),
        ("dependencies[0]", "unsupported"),
    ]


def test_unread_file_citation(tmp_path):
    make_repo(tmp_path)
    # config.yaml exists but is not source, so it is never collected.
    (tmp_path / "config.yaml").write_text("debug: true\n")
    evidence = collect_evidence(analyze_repository(tmp_path))

    data = report_dict()
    data["architecture"][0]["evidence"] = ["config.yaml"]
    report = parse_report(json.dumps(data))

    issues = validate_report(report, evidence)

    assert kinds(issues) == [("architecture[0]", "unread_file")]


@pytest.mark.parametrize("citation, expected", [
    ("app.py", None),
    ("app.py:7", 7),
    ("app.py:2-9", 9),
])
def test_cited_line(citation, expected):
    assert cited_line(citation) == expected


def test_line_out_of_range(tmp_path):
    data = report_dict()
    # app.py has 4 lines.
    data["architecture"][0]["evidence"] = ["app.py:40"]
    report = parse_report(json.dumps(data))

    issues = validate_report(report, evidence_for(tmp_path))

    assert kinds(issues) == [
        ("architecture[0]", "bad_line"),
        ("architecture[0]", "unsupported"),
    ]


def test_line_range_end_checked(tmp_path):
    data = report_dict()
    data["architecture"][0]["evidence"] = ["app.py:2-4", "app.py:3-5"]
    report = parse_report(json.dumps(data))

    issues = validate_report(report, evidence_for(tmp_path))

    assert kinds(issues) == [("architecture[0]", "bad_line")]


@pytest.mark.parametrize("instruction, expected", [
    ("pip install -r requirements.txt", ["requirements.txt"]),
    ("python -m repopilot.cli .", []),
    ("python src/app.py --config=conf/dev.yaml",
     ["src/app.py", "conf/dev.yaml"]),
    ("Run `python app.py`.", ["app.py"]),
    ("curl -O https://example.com/install.sh", []),
    ("pip install .", []),
])
def test_referenced_files(instruction, expected):
    assert referenced_files(instruction) == expected


def test_setup_step_with_missing_file(tmp_path):
    data = report_dict()
    data["setup_steps"] = [
        {"instruction": "pip install -r dev-requirements.txt",
         "evidence": ["README.md"]},
        {"instruction": "pip install -r requirements.txt",
         "evidence": ["README.md"]},
        {"instruction": "cd sub && python app.py",
         "evidence": ["README.md"]},
    ]
    report = parse_report(json.dumps(data))

    issues = validate_report(report, evidence_for(tmp_path))

    assert kinds(issues) == [("setup_steps[0]", "missing_reference")]


def test_line_not_checked_for_truncated_file(tmp_path):
    make_repo(tmp_path)
    evidence = collect_evidence(
        analyze_repository(tmp_path), max_file_chars=10
    )
    data = report_dict()
    data["architecture"][0]["evidence"] = ["app.py:400"]
    report = parse_report(json.dumps(data))

    # The model saw only part of app.py, so line 400 cannot be ruled out.
    assert validate_report(report, evidence) == []


def test_missing_entry_point_path(tmp_path):
    data = report_dict()
    data["entry_points"][0]["path"] = "main.py"
    report = parse_report(json.dumps(data))

    issues = validate_report(report, evidence_for(tmp_path))

    assert kinds(issues) == [("entry_points[0]", "missing_file")]
