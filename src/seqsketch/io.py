"""Strict FASTA and JSONL sequence-record I/O."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from seqsketch.models import SequenceRecord
from seqsketch.sketch import normalize_sequence


def _record(identifier: str, sequence: str, period: int | None = None) -> SequenceRecord:
    return SequenceRecord(
        identifier=identifier, sequence=normalize_sequence(sequence), period=period
    )


def read_fasta(path: Path) -> list[SequenceRecord]:
    """Read multiline FASTA, using the first header token as the identifier."""

    records: list[SequenceRecord] = []
    identifier: str | None = None
    sequence_parts: list[str] = []

    def finish_record() -> None:
        if identifier is not None:
            records.append(_record(identifier, "".join(sequence_parts)))

    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                finish_record()
                header = line[1:].strip()
                if not header:
                    raise ValueError(f"empty FASTA header at line {line_number}")
                identifier = header.split()[0]
                sequence_parts = []
            elif identifier is None:
                raise ValueError(f"sequence before FASTA header at line {line_number}")
            else:
                sequence_parts.append(line)
    finish_record()
    _validate_collection(records)
    return records


def _parse_json_record(value: Any, line_number: int) -> SequenceRecord:
    if not isinstance(value, dict):
        raise TypeError("record is not an object")
    allowed = {"id", "sequence", "period"}
    if not {"id", "sequence"} <= set(value) or not set(value) <= allowed:
        raise ValueError("record must contain id and sequence, with optional period")
    identifier = value["id"]
    sequence = value["sequence"]
    period = value.get("period")
    if not isinstance(identifier, str) or not isinstance(sequence, str):
        raise TypeError("id and sequence must be strings")
    if period is not None and (not isinstance(period, int) or isinstance(period, bool)):
        raise TypeError("period must be an integer or null")
    try:
        return _record(identifier, sequence, period)
    except ValueError as error:
        raise ValueError(f"invalid record at line {line_number}: {error}") from error


def read_jsonl(path: Path) -> list[SequenceRecord]:
    records: list[SequenceRecord] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(_parse_json_record(json.loads(line), line_number))
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                if str(error).startswith("invalid record at line"):
                    raise
                raise ValueError(f"invalid record at line {line_number}: {error}") from error
    _validate_collection(records)
    return records


def _validate_collection(records: list[SequenceRecord]) -> None:
    if not records:
        raise ValueError("input contains no records")
    identifiers = [record.identifier for record in records]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("record identifiers must be unique")


def read_records(path: Path) -> list[SequenceRecord]:
    if path.suffix.lower() in {".fa", ".faa", ".fasta", ".fna"}:
        return read_fasta(path)
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return read_jsonl(path)
    raise ValueError("input extension must be FASTA or JSONL")


def write_jsonl(path: Path, records: list[SequenceRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in sorted(records, key=lambda item: item.identifier):
            value = {"id": record.identifier, "period": record.period, "sequence": record.sequence}
            handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    temporary.replace(path)
