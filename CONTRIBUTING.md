# Contributing

Create a virtual environment, install `.[dev]`, and run `./scripts/verify.sh` before opening a pull
request. Changes to hashing, serialization, ranking, or graph orientation should include tests that
demonstrate determinism and backwards-compatibility implications.

Please keep fixtures synthetic and small. Do not submit private, controlled, or identifying data.

