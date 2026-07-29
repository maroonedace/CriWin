"""Render a JUnit XML report as a Markdown summary for the CI run page.

Reads a JUnit XML file (produced by ``pytest --junitxml``) and prints a
GitHub-flavoured Markdown summary — a totals line plus a per-test table with a
pass/fail/skip status — to stdout. The CI workflow redirects this into
``$GITHUB_STEP_SUMMARY`` so every test's result is visible on the run summary.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

_LABELS = {
    "passed": "✅ passed",
    "failed": "❌ failed",
    "error": "💥 error",
    "skipped": "⏭️ skipped",
}


def _status_of(case: ET.Element) -> str:
    tags = {child.tag for child in case}
    if "failure" in tags:
        return "failed"
    if "error" in tags:
        return "error"
    if "skipped" in tags:
        return "skipped"
    return "passed"


def render(path: str) -> str:
    cases = list(ET.parse(path).getroot().iter("testcase"))

    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    rows = []
    for case in cases:
        status = _status_of(case)
        counts[status] += 1
        name = "::".join(p for p in (case.get("classname"), case.get("name")) if p)
        rows.append((_LABELS[status], name, case.get("time", "")))

    total = len(cases)
    lines = [
        "## Test results",
        "",
        f"**{counts['passed']}/{total} passed** — "
        f"{counts['failed']} failed, {counts['error']} errors, {counts['skipped']} skipped",
        "",
        "| Status | Test | Time (s) |",
        "| ------ | ---- | -------- |",
        *(f"| {label} | {name} | {time} |" for label, name, time in rows),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render(sys.argv[1] if len(sys.argv) > 1 else "junit.xml"))
