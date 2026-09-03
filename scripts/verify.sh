#!/usr/bin/env bash
set -euo pipefail

project_root=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"

python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m pytest
python -m build

smoke_dir=$(mktemp -d "${TMPDIR:-/tmp}/seqsketch.XXXXXX")
trap 'rm -rf "$smoke_dir"' EXIT HUP INT TERM
seqsketch demo --output "$smoke_dir/demo" >/dev/null
seqsketch inspect "$smoke_dir/demo/index.json" >/dev/null
seqsketch query "$smoke_dir/demo/index.json" ACDEFGHIKLMNPQ --exhaustive >/dev/null
seqsketch graph \
  "$smoke_dir/demo/index.json" \
  "$smoke_dir/rebuilt-edges.jsonl" \
  --threshold 0.35 \
  --exhaustive >/dev/null

printf 'All checks passed, including deterministic indexing, querying, and graph construction.\n'

