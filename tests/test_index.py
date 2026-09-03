import json
from pathlib import Path

import pytest

from seqsketch.index import SequenceIndex
from seqsketch.models import SequenceRecord
from seqsketch.sketch import SketchConfig


def _index() -> SequenceIndex:
    records = [
        SequenceRecord("exact", "ACDEFGHIK", 0),
        SequenceRecord("near", "ACDEFGHIL", 1),
        SequenceRecord("far", "YYYYVVVVV", 2),
    ]
    return SequenceIndex.build(
        records,
        SketchConfig(kmer_size=3, num_permutations=64, bands=32, seed=7),
    )


def test_exhaustive_query_ranks_exact_match_first() -> None:
    neighbors = _index().neighbors("ACDEFGHIK", exhaustive=True)
    assert neighbors[0].identifier == "exact"
    assert neighbors[0].jaccard == 1.0
    assert neighbors[-1].identifier == "far"


def test_query_can_exclude_the_source_record() -> None:
    neighbors = _index().neighbors(
        "ACDEFGHIK", exhaustive=True, exclude_identifier="exact", threshold=0.1
    )
    assert [neighbor.identifier for neighbor in neighbors] == ["near"]


def test_lsh_query_returns_exact_match() -> None:
    neighbors = _index().neighbors("ACDEFGHIK")
    assert neighbors[0].identifier == "exact"


def test_index_round_trip_preserves_results(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    index = _index()
    digest = index.save(path)
    loaded = SequenceIndex.load(path)
    assert len(digest) == 64
    assert loaded.records == index.records
    assert loaded.neighbors("ACDEFGHIK", exhaustive=True) == index.neighbors(
        "ACDEFGHIK", exhaustive=True
    )


def test_serialized_index_is_independent_of_input_order(tmp_path: Path) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    index = _index()
    reversed_index = SequenceIndex.build(list(reversed(index.records)), index.config)
    assert index.save(first_path) == reversed_index.save(second_path)
    assert first_path.read_bytes() == second_path.read_bytes()


def test_index_refuses_accidental_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    index = _index()
    index.save(path)
    with pytest.raises(FileExistsError, match="refusing"):
        index.save(path)


def test_loader_rejects_unknown_format(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    path.write_text(json.dumps({"format_version": 99}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        SequenceIndex.load(path)
