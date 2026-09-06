# SeqSketch

[![License](https://img.shields.io/github/license/williamtbarker/seqsketch)](https://github.com/williamtbarker/seqsketch/blob/main/LICENSE)
[![Release](https://img.shields.io/github/v/release/williamtbarker/seqsketch?display_name=tag&sort=semver)](https://github.com/williamtbarker/seqsketch/releases)

[![CI](https://github.com/williamtbarker/seqsketch/actions/workflows/ci.yml/badge.svg)](https://github.com/williamtbarker/seqsketch/actions/workflows/ci.yml)
[![Python 3.10–3.12](https://img.shields.io/badge/python-3.10--3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SeqSketch is a deterministic, dependency-free MinHash/LSH index for symbolic sequences. It turns
FASTA or strict JSONL records into a portable JSON index, performs approximate candidate retrieval
with exact fingerprint-Jaccard reranking, and can construct bounded similarity graphs whose edges
always point from older observations to newer ones.

The package is intended for reproducible experiments, teaching, and modest local datasets. It is
not a replacement for alignment, phylogenetic inference, or a distributed similarity-search
service.

## What it demonstrates

- stable BLAKE2 k-mer fingerprints instead of process-randomized Python hashes;
- reproducible universal-hash MinHash permutations;
- deterministic LSH banding and candidate retrieval;
- exact set-similarity reranking of approximate candidates;
- portable, validated JSON serialization rather than unsafe pickle files;
- strict FASTA and JSONL ingestion with duplicate-ID detection;
- older-to-newer graph orientation, period-gap filtering, and bounded out-degree;
- a typed Python API, CLI, tests, package builds, and Linux/macOS CI.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

SeqSketch has no runtime dependencies outside the Python standard library.

## Run the demo

```bash
seqsketch demo --output artifacts/demo
```

The demo creates six timestamped synthetic sequences, a portable index, ranked neighbors, and a
time-directed similarity edge list. It requires no downloads or private data.

## Build an index

FASTA input uses the first whitespace-delimited header token as the record identifier:

```bash
seqsketch build examples/sequences.fasta artifacts/example-index.json \
  --kmer-size 3 \
  --num-permutations 64 \
  --bands 16
```

Timestamped JSONL supports temporal graphs:

```json
{"id":"sample-001","period":0,"sequence":"ACDEFGHIKLMNPQ"}
{"id":"sample-002","period":1,"sequence":"ACDEFGHIKLMNPR"}
```

```bash
seqsketch build examples/timestamped.jsonl artifacts/temporal-index.json --kmer-size 3
```

## Query

```bash
seqsketch query artifacts/example-index.json ACDEFGHIKLMNPQ \
  --threshold 0.25 \
  --top-k 5
```

The normal query path uses LSH to generate candidates, then reports both exact k-mer-fingerprint
Jaccard and the MinHash estimate. `--exhaustive` compares every indexed record and is useful for
small datasets, evaluation, or cases where recall matters more than speed.

## Construct a temporal graph

```bash
seqsketch graph artifacts/temporal-index.json artifacts/edges.jsonl \
  --threshold 0.35 \
  --max-period-gap 2 \
  --max-out-degree 10
```

Each JSONL edge includes `source`, `target`, `jaccard`, `estimated_jaccard`, and `period_delta`.
Records in the same period are not connected, and every emitted edge satisfies:

```text
source period < target period
```

## Algorithm and reproducibility contract

For each unique overlapping k-mer, SeqSketch computes a 61-bit BLAKE2 fingerprint. A seeded family
of universal hashes produces the minimum value for each permutation. Equal signature positions
estimate set Jaccard similarity. LSH bands retrieve likely matches, after which stored k-mer
fingerprints provide deterministic exact reranking.

An index records every parameter needed to reproduce its signatures. Record order does not affect
the serialized output. The format is versioned, human-readable JSON and is validated when loaded.

## Verification

```bash
./scripts/verify.sh
```

This runs formatting, linting, strict type checking, unit and integration tests, source/wheel
builds, and an end-to-end demo followed by a query and graph inspection.

## Limitations

- Fingerprint collisions are possible, though unlikely with 61-bit values.
- LSH is probabilistic candidate retrieval and can miss true neighbors; use `--exhaustive` when
  completeness is required.
- The pure-Python implementation favors clarity and portability over very large-scale throughput.
- Similarity is alignment-free k-mer set overlap; it does not establish ancestry or function.

## License

MIT. See [LICENSE](LICENSE).
