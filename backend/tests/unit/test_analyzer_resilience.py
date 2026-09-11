from pathlib import Path
from time import perf_counter

from app.analyzers.call_graph_analyzer import CallGraphAnalyzer


def test_call_graph_handles_cycles_and_bad_files(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(
        "from b import second\n\ndef first():\n    return second()\n",
        encoding="utf-8",
    )
    (tmp_path / "b.py").write_text(
        "from a import first\n\ndef second():\n    return first()\n",
        encoding="utf-8",
    )
    result = CallGraphAnalyzer().analyze(
        root=tmp_path,
        files=["a.py", "b.py", "missing.py"],
        endpoints=[],
    )

    calls = [
        relation for relation in result.relations.values() if relation["relation_type"] == "CALLS"
    ]
    assert len(calls) == 2
    assert result.issues[0]["path"] == "missing.py"


def test_call_graph_analyzes_medium_project_within_budget(tmp_path: Path) -> None:
    files: list[str] = []
    for index in range(120):
        relative_path = f"module_{index}.py"
        files.append(relative_path)
        (tmp_path / relative_path).write_text(
            "\n".join(
                [
                    "def leaf(value: int) -> int:",
                    "    return value",
                    "",
                    "def entry(value: int) -> int:",
                    "    return leaf(value)",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    started = perf_counter()
    result = CallGraphAnalyzer().analyze(
        root=tmp_path,
        files=files,
        endpoints=[],
    )
    elapsed = perf_counter() - started

    assert len(result.nodes) == 240
    assert len(result.relations) == 120
    assert elapsed < 10
