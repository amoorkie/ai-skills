"""AST and token based review rules."""

from __future__ import annotations

import ast
from io import StringIO
from pathlib import Path
import re
import tokenize

from ai_skills_toolkit.skills.code_reviewer.analyzers.common import make_finding
from ai_skills_toolkit.skills.code_reviewer.schema import ReviewFinding

TODO_RE = re.compile(r"\b(?:TODO|FIXME)\b")
REQUEST_CALLS = {"get", "post", "put", "patch", "delete", "head", "options", "request"}
SUBPROCESS_CALLS = {"run", "Popen", "call", "check_call", "check_output"}


def _is_test_file(rel_path: str) -> bool:
    return rel_path.startswith("tests/") or "/tests/" in rel_path


def _is_cli_module(rel_path: str) -> bool:
    return Path(rel_path).name in {"cli.py", "__main__.py"}


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _has_keyword(call: ast.Call, name: str, *, truthy: bool | None = None) -> bool:
    for keyword in call.keywords:
        if keyword.arg != name:
            continue
        if truthy is None:
            return True
        if isinstance(keyword.value, ast.Constant) and bool(keyword.value.value) is truthy:
            return True
    return False


def _mutable_default_findings(rel_path: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    defaults = list(node.args.defaults) + list(node.args.kw_defaults)
    for default in defaults:
        if isinstance(default, (ast.List, ast.Dict, ast.Set)):
            findings.append(
                make_finding(
                    rule_id="python.mutable-default-arg",
                    severity="medium",
                    category="correctness",
                    scope="runtime",
                    path=rel_path,
                    line=node.lineno,
                    title="Mutable default argument",
                    detail="Mutable default values are shared across calls and can create hidden state bugs.",
                    recommendation="Use `None` as the default and create the list/dict/set inside the function body.",
                    confidence=0.96,
                    likelihood="high",
                    fix_complexity="small",
                    tests_to_add=[f"Regression test for repeated calls to `{node.name}`."],
                    evidence=[f"Function `{node.name}` declares a mutable default at `{rel_path}:{node.lineno}`."],
                )
            )
            break
    return findings


def extract_ast_findings(rel_path: str, content: str) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    is_test_file = _is_test_file(rel_path)
    cli_module = _is_cli_module(rel_path)

    try:
        tree = ast.parse(content, filename=rel_path)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append(
                    make_finding(
                        rule_id="python.bare-except",
                        severity="high",
                        category="correctness",
                        scope="runtime",
                        path=rel_path,
                        line=node.lineno,
                        title="Bare except",
                        detail="Catches all exceptions and can hide defects.",
                        recommendation="Catch explicit exception types and handle only the failures you expect.",
                        confidence=0.99,
                        impact="high",
                        likelihood="high",
                        fix_complexity="small",
                        tests_to_add=["Test unexpected exceptions are surfaced instead of swallowed."],
                        evidence=[f"Bare exception handler at `{rel_path}:{node.lineno}` catches all failures."],
                    )
                )
            elif isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name) and node.type.id == "Exception":
                findings.append(
                    make_finding(
                        rule_id="python.broad-except-exception",
                        severity="medium",
                        category="correctness",
                        scope="runtime",
                        path=rel_path,
                        line=node.lineno,
                        title="Broad exception handler",
                        detail="`except Exception` can still hide programming errors and make failure modes harder to reason about.",
                        recommendation="Catch narrower exception classes or re-raise unexpected failures after logging context.",
                        confidence=0.92,
                        likelihood="high",
                        fix_complexity="small",
                        tests_to_add=["Test unexpected failures preserve traceback or specific error handling."],
                        evidence=[f"`except Exception` observed at `{rel_path}:{node.lineno}`."],
                    )
                )
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
                findings.append(
                    make_finding(
                        rule_id="python.eval",
                        severity="high",
                        category="security",
                        scope="runtime",
                        path=rel_path,
                        line=node.lineno,
                        title="Use of eval",
                        detail="`eval` can execute arbitrary code and introduces security risks.",
                        recommendation="Replace `eval` with explicit parsing or a safe whitelist-based interpreter.",
                        confidence=0.99,
                        impact="high",
                        likelihood="high",
                        fix_complexity="medium",
                        tests_to_add=["Add a test proving untrusted input cannot trigger arbitrary execution."],
                        evidence=[f"`eval(...)` call observed at `{rel_path}:{node.lineno}`."],
                    )
                )
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
                and not is_test_file
                and not cli_module
            ):
                findings.append(
                    make_finding(
                        rule_id="python.print-debug",
                        severity="low",
                        category="maintainability",
                        scope="single-file",
                        path=rel_path,
                        line=node.lineno,
                        title="Debug print statement",
                        detail="Direct `print` calls are harder to route, filter, and correlate in production code.",
                        recommendation="Use the project logging abstraction or structured logging instead of `print`.",
                        confidence=0.9,
                        impact="low",
                        fix_complexity="small",
                        evidence=[f"`print(...)` call in non-CLI module at `{rel_path}:{node.lineno}`."],
                    )
                )
            elif isinstance(node, ast.Assert) and not is_test_file:
                findings.append(
                    make_finding(
                        rule_id="python.runtime-assert",
                        severity="low",
                        category="correctness",
                        scope="runtime",
                        path=rel_path,
                        line=node.lineno,
                        title="Runtime assert in non-test module",
                        detail="Assertions can be disabled with optimizations.",
                        recommendation="Raise explicit exceptions for runtime validation paths.",
                        confidence=0.97,
                        impact="low",
                        fix_complexity="small",
                        evidence=[f"`assert` used for runtime control flow at `{rel_path}:{node.lineno}`."],
                    )
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                findings.extend(_mutable_default_findings(rel_path, node))
            elif isinstance(node, ast.Call):
                call_name = _call_name(node.func)
                if call_name and call_name.startswith("subprocess.") and call_name.split(".")[-1] in SUBPROCESS_CALLS and _has_keyword(node, "shell", truthy=True):
                    findings.append(
                        make_finding(
                            rule_id="python.subprocess-shell-true",
                            severity="high",
                            category="security",
                            scope="runtime",
                            path=rel_path,
                            line=node.lineno,
                            title="subprocess call with shell=True",
                            detail="`shell=True` expands shell parsing and increases command injection risk.",
                            recommendation="Pass an argument list and keep `shell=False` unless shell semantics are strictly required.",
                            confidence=0.98,
                            impact="high",
                            likelihood="high",
                            fix_complexity="small",
                            tests_to_add=["Add a regression test for safe subprocess argument handling."],
                            evidence=[f"`subprocess` call with `shell=True` at `{rel_path}:{node.lineno}`."],
                        )
                    )
                if call_name and any(call_name.startswith(prefix) for prefix in ("requests.", "httpx.")) and call_name.split(".")[-1] in REQUEST_CALLS and not _has_keyword(node, "timeout"):
                    findings.append(
                        make_finding(
                            rule_id="python.network-no-timeout",
                            severity="medium",
                            category="operability",
                            scope="runtime",
                            path=rel_path,
                            line=node.lineno,
                            title="Network call without timeout",
                            detail="HTTP calls without a timeout can hang indefinitely and create cascading failures.",
                            recommendation="Set an explicit timeout and handle retry/backoff semantics at the call site.",
                            confidence=0.95,
                            likelihood="high",
                            fix_complexity="small",
                            tests_to_add=["Add a test that verifies timeout configuration on outbound network calls."],
                            evidence=[f"HTTP client call without `timeout=` at `{rel_path}:{node.lineno}`."],
                        )
                    )

    try:
        for token in tokenize.generate_tokens(StringIO(content).readline):
            if token.type == tokenize.COMMENT and TODO_RE.search(token.string):
                findings.append(
                    make_finding(
                        rule_id="repo.todo-fixme",
                        severity="medium",
                        category="maintainability",
                        scope="single-file",
                        path=rel_path,
                        line=token.start[0],
                        title="Unresolved TODO/FIXME",
                        detail="Commented TODO/FIXME markers often indicate incomplete work or unclear ownership.",
                        recommendation="Link the work to an issue or remove stale TODO/FIXME markers once resolved.",
                        confidence=0.88,
                        fix_complexity="small",
                        evidence=[f"Comment marker `{token.string.strip()}` at `{rel_path}:{token.start[0]}`."],
                    )
                )
    except tokenize.TokenError:
        pass

    return findings
