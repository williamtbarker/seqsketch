"""Portable MinHash/LSH sequence index."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from seqsketch.models import Neighbor, SequenceRecord
from seqsketch.sketch import (
    SketchConfig,
    band_keys,
    estimated_jaccard,
    fingerprint_jaccard,
    sketch_sequence,
)

FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class IndexedRecord:
    record: SequenceRecord
    signature: tuple[int, ...]
    fingerprints: tuple[int, ...]


class SequenceIndex:
    """In-memory LSH index with portable, non-pickle serialization."""

    def __init__(self, config: SketchConfig, entries: list[IndexedRecord]) -> None:
        if not entries:
            raise ValueError("index requires at least one record")
        self.config = config
        self._entries = {entry.record.identifier: entry for entry in entries}
        if len(self._entries) != len(entries):
            raise ValueError("record identifiers must be unique")
        self._buckets: dict[tuple[int, ...], set[str]] = {}
        for entry in entries:
            if len(entry.signature) != config.num_permutations or not entry.fingerprints:
                raise ValueError("entry is incompatible with index configuration")
            for key in band_keys(entry.signature, config):
                self._buckets.setdefault(key, set()).add(entry.record.identifier)

    @classmethod
    def build(cls, records: list[SequenceRecord], config: SketchConfig) -> SequenceIndex:
        entries = []
        for record in sorted(records, key=lambda item: item.identifier):
            signature, fingerprints = sketch_sequence(record.sequence, config)
            entries.append(IndexedRecord(record, signature, fingerprints))
        return cls(config, entries)

    @property
    def records(self) -> tuple[SequenceRecord, ...]:
        return tuple(self._entries[key].record for key in sorted(self._entries))

    def candidate_ids(self, signature: tuple[int, ...]) -> set[str]:
        candidates: set[str] = set()
        for key in band_keys(signature, self.config):
            candidates.update(self._buckets.get(key, set()))
        return candidates

    def neighbors(
        self,
        sequence: str,
        *,
        threshold: float = 0.0,
        top_k: int = 10,
        exhaustive: bool = False,
        exclude_identifier: str | None = None,
    ) -> list[Neighbor]:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        query_signature, query_fingerprints = sketch_sequence(sequence, self.config)
        candidate_ids = set(self._entries) if exhaustive else self.candidate_ids(query_signature)
        if exclude_identifier is not None:
            candidate_ids.discard(exclude_identifier)
        neighbors = []
        for identifier in candidate_ids:
            entry = self._entries[identifier]
            exact = fingerprint_jaccard(query_fingerprints, entry.fingerprints)
            if exact >= threshold:
                neighbors.append(
                    Neighbor(
                        identifier=identifier,
                        jaccard=exact,
                        estimated_jaccard=estimated_jaccard(query_signature, entry.signature),
                    )
                )
        return sorted(
            neighbors,
            key=lambda item: (-item.jaccard, -item.estimated_jaccard, item.identifier),
        )[:top_k]

    def entry(self, identifier: str) -> IndexedRecord:
        try:
            return self._entries[identifier]
        except KeyError as error:
            raise KeyError(f"unknown record identifier: {identifier}") from error

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": FORMAT_VERSION,
            "config": self.config.to_dict(),
            "records": [
                {
                    "id": entry.record.identifier,
                    "sequence": entry.record.sequence,
                    "period": entry.record.period,
                    "signature": list(entry.signature),
                    "fingerprints": list(entry.fingerprints),
                }
                for entry in (self._entries[key] for key in sorted(self._entries))
            ],
        }

    def save(self, path: Path, *, force: bool = False) -> str:
        if path.exists() and not force:
            raise FileExistsError(f"refusing to overwrite existing index: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n").encode()
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(encoded)
        temporary.replace(path)
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def load(cls, path: Path) -> SequenceIndex:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or value.get("format_version") != FORMAT_VERSION:
                raise ValueError("unsupported index format")
            config_value = cast(dict[str, Any], value["config"])
            config = SketchConfig(**config_value)
            records_value = value["records"]
            if not isinstance(records_value, list):
                raise TypeError("records must be a list")
            entries = [_entry_from_dict(item) for item in records_value]
            return cls(config, entries)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid index {path}: {error}") from error


def _integer_tuple(value: Any, field: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise TypeError(f"{field} must be a non-empty integer list")
    if any(not isinstance(item, int) or isinstance(item, bool) for item in value):
        raise TypeError(f"{field} must be a non-empty integer list")
    return tuple(value)


def _entry_from_dict(value: Any) -> IndexedRecord:
    if not isinstance(value, dict):
        raise TypeError("index record must be an object")
    identifier = value["id"]
    sequence = value["sequence"]
    period = value["period"]
    if not isinstance(identifier, str) or not isinstance(sequence, str):
        raise TypeError("index id and sequence must be strings")
    if period is not None and (not isinstance(period, int) or isinstance(period, bool)):
        raise TypeError("index period must be an integer or null")
    record = SequenceRecord(identifier, sequence, period)
    return IndexedRecord(
        record,
        _integer_tuple(value["signature"], "signature"),
        _integer_tuple(value["fingerprints"], "fingerprints"),
    )
