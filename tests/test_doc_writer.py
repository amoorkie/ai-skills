from __future__ import annotations

from pathlib import Path

from ai_skills_toolkit.skills.doc_writer import DocWriterInput, generate_document, run


def test_doc_writer_generates_markdown_from_repo_analysis(sample_repo: Path) -> None:
    markdown = generate_document(DocWriterInput(repo_path=sample_repo, title="Repo Doc"))
    assert "# Repo Doc" in markdown
    assert "## Repository Snapshot" in markdown
    assert "## Technology Signals" in markdown
    assert "Python" in markdown


def test_doc_writer_writes_output(sample_repo: Path, tmp_path: Path) -> None:
    result = run(DocWriterInput(repo_path=sample_repo), output_dir=tmp_path / "generated", output_name="doc")
    assert result.output_path.exists()
    assert "doc_writer" in str(result.output_path)


def test_doc_writer_can_skip_setup_checklist(sample_repo: Path) -> None:
    markdown = generate_document(DocWriterInput(repo_path=sample_repo, include_setup_checklist=False))
    assert "## Setup Checklist" not in markdown
