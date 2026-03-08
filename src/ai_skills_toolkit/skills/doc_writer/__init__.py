"""Documentation writer skill."""

from ai_skills_toolkit.skills.doc_writer.schema import DocWriterInput
from ai_skills_toolkit.skills.doc_writer.eval import run_builtin_evaluation
from ai_skills_toolkit.skills.doc_writer.skill import generate_document, run

__all__ = ["DocWriterInput", "generate_document", "run", "run_builtin_evaluation"]
