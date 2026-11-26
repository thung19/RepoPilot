"""Shared helpers for LLM tests. No test talks to a real model."""

import json

from repopilot.llm.client import LLMResponse


def make_repo(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Demo\n\nRun with `python app.py`.\n"
    )
    (tmp_path / "requirements.txt").write_text("flask\n")
    (tmp_path / "app.py").write_text(
        "from flask import Flask\n"
        "app = Flask(__name__)\n"
        'if __name__ == "__main__":\n'
        "    app.run()\n"
    )
    (tmp_path / "utils.py").write_text("def helper():\n    pass\n")
    return tmp_path


def report_dict(**overrides):
    report = {
        "purpose": {
            "statement": "A small Flask web app.",
            "evidence": ["README.md", "app.py"],
        },
        "architecture": [
            {
                "name": "app",
                "responsibility": "Creates and runs the Flask app.",
                "evidence": ["app.py:2"],
            }
        ],
        "entry_points": [
            {
                "path": "app.py",
                "description": "Run directly with python.",
                "evidence": ["app.py"],
            }
        ],
        "dependencies": [
            {
                "name": "flask",
                "purpose": "Web framework.",
                "evidence": ["requirements.txt"],
            }
        ],
        "setup_steps": [
            {
                "instruction": "python app.py",
                "evidence": ["README.md"],
            }
        ],
        "unknowns": ["Which Python version is required?"],
    }
    report.update(overrides)
    return report


class FakeClient:
    def __init__(self, text, max_prompt_chars=1_000_000):
        self.text = text
        self.max_prompt_chars = max_prompt_chars
        self.calls = []

    def generate(self, system, user, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        return LLMResponse(
            text=self.text,
            model="fake-model",
            input_tokens=100,
            output_tokens=50,
            duration_seconds=0.5,
        )


def fake_client(**overrides):
    return FakeClient(json.dumps(report_dict(**overrides)))
