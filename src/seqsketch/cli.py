"""Command-line interface for building and querying portable sequence indexes."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from seqsketch.graph import temporal_edges, write_edges
from seqsketch.index import SequenceIndex
from seqsketch.io import read_records, write_jsonl
from seqsketch.models import SequenceRecord
from seqsketch.sketch import SketchConfig

_DEMO_ARTIFACTS = {"edges.jsonl", "index.json", "neighbors.json", "sequences.jsonl"}


def _add_index_parameters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--kmer-size", type=int, default=5)
    parser.add_argument("--num-permutations", type=int, default=64)
    parser.add_argument("--bands", type=int, default=16)
    parser.add_argument("--seed", type=int, default=17)


def _config(arguments: argparse.Namespace) -> SketchConfig:
    return SketchConfig(
        kmer_size=arguments.kmer_size,
        num_permutations=arguments.num_permutations,
        bands=arguments.bands,
        seed=arguments.seed,
    )


def _json_print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _build(arguments: argparse.Namespace) -> None:
    records = read_records(arguments.input)
    index = SequenceIndex.build(records, _config(arguments))
    digest = index.save(arguments.output, force=arguments.force)
    _json_print(
        {
            "index": str(arguments.output),
            "records": len(records),
            "sha256": digest,
        }
    )


def _query(arguments: argparse.Namespace) -> None:
    index = SequenceIndex.load(arguments.index)
    neighbors = index.neighbors(
        arguments.sequence,
        threshold=arguments.threshold,
        top_k=arguments.top_k,
        exhaustive=arguments.exhaustive,
        exclude_identifier=arguments.exclude,
    )
    _json_print([asdict(neighbor) for neighbor in neighbors])


def _graph(arguments: argparse.Namespace) -> None:
    index = SequenceIndex.load(arguments.index)
    edges = temporal_edges(
        index,
        threshold=arguments.threshold,
        max_period_gap=arguments.max_period_gap,
        max_out_degree=arguments.max_out_degree,
        exhaustive=arguments.exhaustive,
    )
    write_edges(arguments.output, edges, force=arguments.force)
    _json_print({"edges": len(edges), "output": str(arguments.output)})


def _inspect(arguments: argparse.Namespace) -> None:
    index = SequenceIndex.load(arguments.index)
    periods = sorted({record.period for record in index.records if record.period is not None})
    _json_print(
        {
            "config": index.config.to_dict(),
            "periods": periods,
            "records": len(index.records),
        }
    )


def _demo_records() -> list[SequenceRecord]:
    return [
        SequenceRecord("alpha-0", "ACDEFGHIKLMNPQ", 0),
        SequenceRecord("alpha-1", "ACDEFGHIKLMNPR", 1),
        SequenceRecord("alpha-2", "ACDEFGHIKLMNTR", 2),
        SequenceRecord("beta-0", "RSTVWYACDEFGHI", 0),
        SequenceRecord("beta-1", "RSTVWYACDEFGHV", 1),
        SequenceRecord("outlier", "YYYYYYYYVVVVVV", 2),
    ]


def _prepare_demo_directory(path: Path, force: bool) -> None:
    if path.exists():
        unexpected = {item.name for item in path.iterdir()} - _DEMO_ARTIFACTS
        if unexpected:
            joined = ", ".join(sorted(unexpected))
            raise ValueError(f"refusing to use output directory with unrelated files: {joined}")
        if any(path.iterdir()) and not force:
            raise FileExistsError(f"demo output already exists: {path}; pass --force")
    path.mkdir(parents=True, exist_ok=True)


def _demo(arguments: argparse.Namespace) -> None:
    _prepare_demo_directory(arguments.output, arguments.force)
    records = _demo_records()
    data_path = arguments.output / "sequences.jsonl"
    index_path = arguments.output / "index.json"
    edges_path = arguments.output / "edges.jsonl"
    neighbors_path = arguments.output / "neighbors.json"
    write_jsonl(data_path, records)
    index = SequenceIndex.build(records, SketchConfig())
    index.save(index_path, force=True)
    edges = temporal_edges(index, threshold=0.35, exhaustive=True)
    write_edges(edges_path, edges, force=True)
    neighbors = index.neighbors(records[1].sequence, top_k=3, exhaustive=True)
    neighbors_path.write_text(
        json.dumps([asdict(neighbor) for neighbor in neighbors], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _json_print(
        {
            "edges": len(edges),
            "nearest": neighbors[0].identifier,
            "output": str(arguments.output),
            "records": len(records),
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seqsketch",
        description="Build deterministic MinHash/LSH indexes for symbolic sequences.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build a portable index from FASTA or JSONL")
    build.add_argument("input", type=Path)
    build.add_argument("output", type=Path)
    _add_index_parameters(build)
    build.add_argument("--force", action="store_true")
    build.set_defaults(handler=_build)

    query = subparsers.add_parser("query", help="Find similar indexed records")
    query.add_argument("index", type=Path)
    query.add_argument("sequence")
    query.add_argument("--threshold", type=float, default=0.0)
    query.add_argument("--top-k", type=int, default=10)
    query.add_argument("--exclude")
    query.add_argument("--exhaustive", action="store_true")
    query.set_defaults(handler=_query)

    graph = subparsers.add_parser("graph", help="Build older-to-newer similarity edges")
    graph.add_argument("index", type=Path)
    graph.add_argument("output", type=Path)
    graph.add_argument("--threshold", type=float, default=0.5)
    graph.add_argument("--max-period-gap", type=int)
    graph.add_argument("--max-out-degree", type=int, default=10)
    graph.add_argument("--exhaustive", action="store_true")
    graph.add_argument("--force", action="store_true")
    graph.set_defaults(handler=_graph)

    inspect = subparsers.add_parser("inspect", help="Summarize a saved index")
    inspect.add_argument("index", type=Path)
    inspect.set_defaults(handler=_inspect)

    demo = subparsers.add_parser("demo", help="Run a deterministic end-to-end example")
    demo.add_argument("--output", type=Path, default=Path("artifacts/demo"))
    demo.add_argument("--force", action="store_true")
    demo.set_defaults(handler=_demo)
    return parser


def main(arguments: list[str] | None = None) -> None:
    parser = build_parser()
    parsed = parser.parse_args(arguments)
    try:
        parsed.handler(parsed)
    except (FileExistsError, KeyError, OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main(sys.argv[1:])
