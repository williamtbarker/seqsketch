"""Deterministic k-mer fingerprints and MinHash signatures."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

_MERSENNE_PRIME = (1 << 61) - 1
_PERSON = b"seqsketch-v1"


@dataclass(frozen=True, slots=True)
class SketchConfig:
    """Parameters that define compatible sketches and LSH bands."""

    kmer_size: int = 5
    num_permutations: int = 64
    bands: int = 16
    seed: int = 17

    def __post_init__(self) -> None:
        if self.kmer_size <= 0:
            raise ValueError("kmer_size must be positive")
        if self.num_permutations < 8:
            raise ValueError("num_permutations must be at least 8")
        if self.bands <= 0 or self.num_permutations % self.bands != 0:
            raise ValueError("bands must be positive and divide num_permutations")
        if self.seed < 0:
            raise ValueError("seed must be non-negative")

    @property
    def rows_per_band(self) -> int:
        return self.num_permutations // self.bands

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_sequence(sequence: str) -> str:
    """Remove whitespace, uppercase, and validate a symbolic sequence."""

    normalized = "".join(sequence.split()).upper()
    if not normalized or not normalized.isascii() or not normalized.isalpha():
        raise ValueError("sequence must contain only ASCII letters and whitespace")
    return normalized


def kmers(sequence: str, kmer_size: int) -> frozenset[str]:
    """Return unique overlapping k-mers from a normalized sequence."""

    if kmer_size <= 0:
        raise ValueError("kmer_size must be positive")
    normalized = normalize_sequence(sequence)
    if len(normalized) < kmer_size:
        raise ValueError("sequence is shorter than kmer_size")
    return frozenset(
        normalized[offset : offset + kmer_size] for offset in range(len(normalized) - kmer_size + 1)
    )


def token_fingerprint(token: str) -> int:
    """Return a stable 61-bit BLAKE2 fingerprint for one token."""

    digest = hashlib.blake2b(token.encode("ascii"), digest_size=8, person=_PERSON).digest()
    return int.from_bytes(digest, "big") % _MERSENNE_PRIME


def sequence_fingerprints(sequence: str, kmer_size: int) -> tuple[int, ...]:
    return tuple(sorted(token_fingerprint(token) for token in kmers(sequence, kmer_size)))


def _coefficient(seed: int, permutation: int, label: bytes) -> int:
    payload = seed.to_bytes(16, "big") + permutation.to_bytes(8, "big") + label
    digest = hashlib.blake2b(payload, digest_size=8, person=_PERSON).digest()
    return int.from_bytes(digest, "big")


def create_signature(fingerprints: tuple[int, ...], config: SketchConfig) -> tuple[int, ...]:
    """Create a classic MinHash signature using stable universal hashes."""

    if not fingerprints:
        raise ValueError("cannot sketch an empty token set")
    signature: list[int] = []
    for permutation in range(config.num_permutations):
        coefficient_a = 1 + _coefficient(config.seed, permutation, b"a") % (_MERSENNE_PRIME - 1)
        coefficient_b = _coefficient(config.seed, permutation, b"b") % _MERSENNE_PRIME
        signature.append(
            min(
                (coefficient_a * fingerprint + coefficient_b) % _MERSENNE_PRIME
                for fingerprint in fingerprints
            )
        )
    return tuple(signature)


def sketch_sequence(sequence: str, config: SketchConfig) -> tuple[tuple[int, ...], tuple[int, ...]]:
    fingerprints = sequence_fingerprints(sequence, config.kmer_size)
    return create_signature(fingerprints, config), fingerprints


def estimated_jaccard(first: tuple[int, ...], second: tuple[int, ...]) -> float:
    """Estimate Jaccard similarity from equal MinHash positions."""

    if not first or len(first) != len(second):
        raise ValueError("signatures must be non-empty and have equal length")
    return sum(left == right for left, right in zip(first, second, strict=True)) / len(first)


def fingerprint_jaccard(first: tuple[int, ...], second: tuple[int, ...]) -> float:
    """Compute exact set Jaccard over stable k-mer fingerprints."""

    first_set = set(first)
    second_set = set(second)
    union = first_set | second_set
    if not union:
        return 1.0
    return len(first_set & second_set) / len(union)


def band_keys(signature: tuple[int, ...], config: SketchConfig) -> tuple[tuple[int, ...], ...]:
    """Split a compatible signature into deterministic LSH band keys."""

    if len(signature) != config.num_permutations:
        raise ValueError("signature length does not match configuration")
    width = config.rows_per_band
    return tuple(
        (band, *signature[band * width : (band + 1) * width]) for band in range(config.bands)
    )
