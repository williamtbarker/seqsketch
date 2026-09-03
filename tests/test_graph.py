from seqsketch.graph import temporal_edges
from seqsketch.index import SequenceIndex
from seqsketch.models import SequenceRecord
from seqsketch.sketch import SketchConfig


def _temporal_index() -> SequenceIndex:
    records = [
        SequenceRecord("old", "ACDEFGHIK", 0),
        SequenceRecord("middle", "ACDEFGHIL", 1),
        SequenceRecord("new", "ACDEFGHIM", 3),
        SequenceRecord("unrelated", "YYYYVVVVV", 2),
    ]
    return SequenceIndex.build(records, SketchConfig(kmer_size=3, num_permutations=32, bands=8))


def test_temporal_edges_always_point_forward() -> None:
    index = _temporal_index()
    edges = temporal_edges(index, threshold=0.2, exhaustive=True)
    periods = {record.identifier: record.period for record in index.records}
    assert edges
    assert all(periods[edge.source] < periods[edge.target] for edge in edges)


def test_period_gap_and_out_degree_are_enforced() -> None:
    edges = temporal_edges(
        _temporal_index(),
        threshold=0.2,
        max_period_gap=1,
        max_out_degree=1,
        exhaustive=True,
    )
    assert all(edge.period_delta <= 1 for edge in edges)
    assert len({edge.source for edge in edges}) == len(edges)


def test_temporal_graph_requires_periods() -> None:
    index = SequenceIndex.build(
        [SequenceRecord("one", "ACDEFG")],
        SketchConfig(kmer_size=3),
    )
    try:
        temporal_edges(index)
    except ValueError as error:
        assert "every record" in str(error)
    else:
        raise AssertionError("expected missing periods to fail")
