from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.doc_writer import DocWriterInput, generate_document, run


def test_doc_writer_generates_markdown_from_repo_analysis(sample_repo: Path) -> None:
    markdown = generate_document(DocWriterInput(repo_path=sample_repo, title="Repo Doc"))
    assert "# Repo Doc" in markdown
    assert "## Repository Snapshot" in markdown
    assert "## Technology Signals" in markdown
    assert "## Audience Guidance" in markdown
    assert "Python" in markdown


def test_doc_writer_writes_output(sample_repo: Path, tmp_path: Path) -> None:
    result = run(DocWriterInput(repo_path=sample_repo), output_dir=tmp_path / "generated", output_name="doc")
    assert result.output_path.exists()
    assert "doc_writer" in str(result.output_path)
    assert result.metadata["artifact_type"] == "repository_documentation"
    assert result.metadata["subject_type"] == "repository"
    assert result.metadata["output_format"] == "markdown"


def test_doc_writer_can_skip_setup_checklist(sample_repo: Path) -> None:
    markdown = generate_document(DocWriterInput(repo_path=sample_repo, include_setup_checklist=False))
    assert "## Setup Checklist" not in markdown


def test_doc_writer_hides_top_level_hidden_entries_by_default(sample_repo: Path) -> None:
    (sample_repo / ".env").write_text("TOKEN=secret\n", encoding="utf-8")

    markdown = generate_document(DocWriterInput(repo_path=sample_repo, title="Repo Doc"))

    assert "`README.md`" in markdown
    assert "`.env`" not in markdown


def test_doc_writer_adapts_to_ai_agent_audience(sample_repo: Path) -> None:
    markdown = generate_document(
        DocWriterInput(
            repo_path=sample_repo,
            title="Agent Doc",
            audience="AI agents",
        )
    )

    assert "Agent operating notes and repository navigation map" in markdown
    assert "Use the runtime signals, key files, and top-level structure below" in markdown


def test_doc_writer_setup_checklist_reflects_detected_signals(sample_repo: Path) -> None:
    (sample_repo / "tests").mkdir()
    (sample_repo / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (sample_repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")

    markdown = generate_document(DocWriterInput(repo_path=sample_repo, title="Repo Doc"))

    assert "Install Python dependencies from `pyproject.toml` or `requirements.txt`." in markdown
    assert "Verify container build assumptions before relying on local runtime parity." in markdown
    assert "Run the detected test suite before making behavioral changes." in markdown
