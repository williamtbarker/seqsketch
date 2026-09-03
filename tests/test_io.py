import json
from pathlib import Path

import pytest

from seqsketch.io import read_fasta, read_jsonl, read_records, write_jsonl
from seqsketch.models import SequenceRecord


def test_reads_multiline_fasta(tmp_path: Path) -> None:
    path = tmp_path / "records.fasta"
    path.write_text(">one description\nacd\nef\n>two\nGGGGGG\n", encoding="utf-8")
    assert read_fasta(path) == [
        SequenceRecord("one", "ACDEF"),
        SequenceRecord("two", "GGGGGG"),
    ]


def test_fasta_requires_unique_identifiers(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.fa"
    path.write_text(">one\nAAAAAA\n>one\nCCCCCC\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        read_fasta(path)


def test_jsonl_round_trip_is_canonical(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    records = [SequenceRecord("later", "ACDEFG", 2), SequenceRecord("early", "ACDEFA", 0)]
    write_jsonl(path, records)
    assert read_jsonl(path) == list(reversed(records))
    assert path.read_text(encoding="utf-8").splitlines()[0].startswith('{"id":"early"')


@pytest.mark.parametrize("period", [1.5, "1", True])
def test_jsonl_rejects_non_integer_period(tmp_path: Path, period: object) -> None:
    path = tmp_path / "invalid.jsonl"
    value = {"id": "one", "period": period, "sequence": "ACDEFG"}
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        read_jsonl(path)


def test_dispatch_rejects_unknown_extension(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="extension"):
        read_records(tmp_path / "records.csv")
