# MacBook setup

From the extracted project directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
./scripts/verify.sh
```

Python 3.10 through 3.12 is supported. The package has no compiled runtime dependencies and does
not require Homebrew, a GPU, or network access after installation.

