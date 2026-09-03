"""Time-directed similarity graph construction."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from seqsketch.index import SequenceIndex
from seqsketch.models import TemporalEdge
from seqsketch.sketch import estimated_jaccard, fingerprint_jaccard


def temporal_edges(
    index: SequenceIndex,
    *,
    threshold: float = 0.5,
    max_period_gap: int | None = None,
    max_out_degree: int = 10,
    exhaustive: bool = False,
) -> list[TemporalEdge]:
    """Connect older records to similar newer records with bounded out-degree."""

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    if max_period_gap is not None and max_period_gap <= 0:
        raise ValueError("max_period_gap must be positive")
    if max_out_degree <= 0:
        raise ValueError("max_out_degree must be positive")
    if any(record.period is None for record in index.records):
        raise ValueError("every record must have a period for temporal graph construction")

    outgoing: dict[str, list[TemporalEdge]] = defaultdict(list)
    for source in index.records:
        source_period = source.period
        assert source_period is not None
        source_entry = index.entry(source.identifier)
        candidate_ids = (
            {record.identifier for record in index.records}
            if exhaustive
            else index.candidate_ids(source_entry.signature)
        )
        candidate_ids.discard(source.identifier)
        for target_id in candidate_ids:
            target_entry = index.entry(target_id)
            target_period = target_entry.record.period
            assert target_period is not None
            period_delta = target_period - source_period
            if period_delta <= 0:
                continue
            if max_period_gap is not None and period_delta > max_period_gap:
                continue
            exact = fingerprint_jaccard(source_entry.fingerprints, target_entry.fingerprints)
            if exact < threshold:
                continue
            outgoing[source.identifier].append(
                TemporalEdge(
                    source=source.identifier,
                    target=target_id,
                    jaccard=exact,
                    estimated_jaccard=estimated_jaccard(
                        source_entry.signature, target_entry.signature
                    ),
                    period_delta=period_delta,
                )
            )

    edges: list[TemporalEdge] = []
    for source_id in sorted(outgoing):
        ranked = sorted(
            outgoing[source_id],
            key=lambda edge: (-edge.jaccard, edge.period_delta, edge.target),
        )
        edges.extend(ranked[:max_out_degree])
    return edges


def write_edges(path: Path, edges: list[TemporalEdge], *, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing edge file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for edge in edges:
            handle.write(
                json.dumps(
                    {
                        "estimated_jaccard": edge.estimated_jaccard,
                        "jaccard": edge.jaccard,
                        "period_delta": edge.period_delta,
                        "source": edge.source,
                        "target": edge.target,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
    temporary.replace(path)
