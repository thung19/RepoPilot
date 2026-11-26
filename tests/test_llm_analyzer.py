import sys

import pytest

from llm_fakes import FakeClient, fake_client, make_repo
from repopilot import cli
from repopilot.llm.analyzer import analyze_with_llm
from repopilot.llm.client import LLMError
from repopilot.llm.report import render_llm_report
from repopilot.llm.schema import LLMReport
from repopilot.pipeline import analyze_repository


def test_prompt_contains_evidence_and_schema(tmp_path):
    analysis = analyze_repository(make_repo(tmp_path))
    client = fake_client()

    analyze_with_llm(analysis, client)

    call = client.calls[0]
    assert call["schema"] == LLMReport.model_json_schema()
    assert '"setup_steps"' in call["system"]
    assert "untrusted" in call["system"]
    assert '<file path="app.py">' in call["user"]
    assert call["user"].rstrip().endswith("</evidence>")


def test_analysis_result(tmp_path):
    analysis = analyze_repository(make_repo(tmp_path))

    result = analyze_with_llm(analysis, fake_client())

    assert result.issues == []
    assert result.report.dependencies[0].name == "flask"
    assert result.response.model == "fake-model"


def test_evidence_shrinks_to_fit_context(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "big.py").write_text("x = 1\n" * 2000)
    analysis = analyze_repository(tmp_path)

    roomy = fake_client()
    analyze_with_llm(analysis, roomy)
    full_size = sum(len(v) for v in roomy.calls[0].values() if isinstance(v, str))

    limit = full_size - 5000
    tight = FakeClient(roomy.text, max_prompt_chars=limit)
    result = analyze_with_llm(analysis, tight)

    call = tight.calls[0]
    assert len(call["system"]) + len(call["user"]) <= limit
    big = [d for d in result.evidence.documents if d.path == "big.py"]
    assert big and big[0].truncated


def test_metadata_too_large_for_context(tmp_path):
    analysis = analyze_repository(make_repo(tmp_path))

    with pytest.raises(LLMError, match="does not fit"):
        analyze_with_llm(analysis, FakeClient("{}", max_prompt_chars=100))


def test_invalid_model_output_raises(tmp_path):
    analysis = analyze_repository(make_repo(tmp_path))

    with pytest.raises(LLMError):
        analyze_with_llm(analysis, FakeClient("not json"))


def test_render_report(tmp_path):
    analysis = analyze_repository(make_repo(tmp_path))
    result = analyze_with_llm(analysis, fake_client())

    text = render_llm_report(result)

    assert "# Repository Onboarding Guide" in text
    assert "**app**: Creates and runs the Flask app." in text
    assert "Sources: `app.py:2`" in text
    assert "## Setup (Unverified)" in text
    assert "- Which Python version is required?" in text
    assert "All citations refer to existing files" in text
    assert "- Tokens: 100 in, 50 out" in text


def test_render_flags_problems(tmp_path):
    analysis = analyze_repository(make_repo(tmp_path))
    client = fake_client(dependencies=[{
        "name": "django",
        "purpose": "Web framework.\n\n# injected heading",
        "evidence": ["Pipfile"],
    }])
    result = analyze_with_llm(analysis, client)

    text = render_llm_report(result)

    assert (
        "- **[unsupported]** **django**: Web framework. # injected heading"
        in text
    )
    assert "`Pipfile` (name only)" in text
    assert "(missing_file): Cited file does not exist: Pipfile" in text


def test_render_flags_setup_step_to_check(tmp_path):
    analysis = analyze_repository(make_repo(tmp_path))
    client = fake_client(setup_steps=[{
        "instruction": "pip install -r requirements-dev.txt",
        "evidence": ["README.md"],
    }])

    text = render_llm_report(analyze_with_llm(analysis, client))

    assert "- **[check]** pip install -r requirements-dev.txt" in text


def run_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["repopilot", *args])
    cli.main()


def test_cli_llm_mode(tmp_path, monkeypatch, capsys):
    (tmp_path / "repo").mkdir()
    repo = make_repo(tmp_path / "repo")
    output = tmp_path / "guide.md"
    used = {}

    def fake_ollama(model, host):
        used["model"] = model
        return fake_client()

    monkeypatch.setattr(cli, "OllamaClient", fake_ollama)

    run_cli(
        monkeypatch, str(repo), "--output", str(output),
        "--llm", "--model", "qwen3:8b",
    )

    assert used["model"] == "qwen3:8b"
    assert "# Repository Onboarding Guide" in output.read_text()
    assert "Report generated" in capsys.readouterr().out


def test_cli_llm_error_exits_cleanly(tmp_path, monkeypatch):
    (tmp_path / "repo").mkdir()
    repo = make_repo(tmp_path / "repo")
    output = tmp_path / "guide.md"

    monkeypatch.setattr(
        cli, "OllamaClient", lambda model, host: FakeClient("not json")
    )

    with pytest.raises(SystemExit) as exit_info:
        run_cli(monkeypatch, str(repo), "--output", str(output), "--llm")

    assert "does not match the report schema" in str(exit_info.value.code)
    assert not output.exists()


def test_cli_default_is_v0(tmp_path, monkeypatch):
    (tmp_path / "repo").mkdir()
    repo = make_repo(tmp_path / "repo")
    output = tmp_path / "report.md"

    def fail(*args, **kwargs):
        raise AssertionError("V0 mode must not create an LLM client")

    monkeypatch.setattr(cli, "OllamaClient", fail)

    run_cli(monkeypatch, str(repo), "--output", str(output))

    assert output.read_text().startswith("# Repository Analysis")
