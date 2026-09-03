import json
from pathlib import Path

import pytest

from seqsketch.cli import main


def test_demo_builds_inspectable_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "demo"
    main(["demo", "--output", str(output)])
    result = json.loads(capsys.readouterr().out)
    assert result["records"] == 6
    assert result["edges"] > 0
    assert result["nearest"] == "alpha-1"
    assert {path.name for path in output.iterdir()} == {
        "edges.jsonl",
        "index.json",
        "neighbors.json",
        "sequences.jsonl",
    }


def test_build_query_and_inspect_workflow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fasta = tmp_path / "records.fasta"
    index = tmp_path / "index.json"
    fasta.write_text(">one\nACDEFGHIK\n>two\nACDEFGHIL\n", encoding="utf-8")
    main(["build", str(fasta), str(index), "--kmer-size", "3"])
    build_result = json.loads(capsys.readouterr().out)
    assert build_result["records"] == 2
    main(["query", str(index), "ACDEFGHIK", "--exhaustive"])
    query_result = json.loads(capsys.readouterr().out)
    assert query_result[0]["identifier"] == "one"
    main(["inspect", str(index)])
    inspect_result = json.loads(capsys.readouterr().out)
    assert inspect_result["records"] == 2


def test_demo_refuses_unrelated_output_files(tmp_path: Path) -> None:
    output = tmp_path / "demo"
    output.mkdir()
    (output / "keep.txt").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(SystemExit) as raised:
        main(["demo", "--output", str(output), "--force"])
    assert raised.value.code == 2
    assert (output / "keep.txt").read_text(encoding="utf-8") == "do not overwrite"
