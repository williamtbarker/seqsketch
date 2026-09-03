import pytest

from seqsketch.sketch import (
    SketchConfig,
    estimated_jaccard,
    fingerprint_jaccard,
    kmers,
    normalize_sequence,
    sketch_sequence,
)


def test_normalization_and_overlapping_kmers() -> None:
    assert normalize_sequence(" acd\nef ") == "ACDEF"
    assert kmers("ACDEF", 3) == {"ACD", "CDE", "DEF"}


def test_short_sequence_is_rejected() -> None:
    with pytest.raises(ValueError, match="shorter"):
        kmers("AC", 3)


def test_configuration_requires_even_bands() -> None:
    with pytest.raises(ValueError, match="divide"):
        SketchConfig(num_permutations=63, bands=16)


def test_sketches_are_deterministic() -> None:
    config = SketchConfig(kmer_size=3, num_permutations=32, bands=8, seed=9)
    assert sketch_sequence("ACDEFG", config) == sketch_sequence("ACDEFG", config)


def test_identical_sequences_have_unit_similarity() -> None:
    config = SketchConfig(kmer_size=3, num_permutations=32, bands=8)
    first_signature, first_tokens = sketch_sequence("ACDEFG", config)
    second_signature, second_tokens = sketch_sequence("ACDEFG", config)
    assert estimated_jaccard(first_signature, second_signature) == 1.0
    assert fingerprint_jaccard(first_tokens, second_tokens) == 1.0


def test_disjoint_sequences_have_zero_fingerprint_jaccard() -> None:
    config = SketchConfig(kmer_size=3)
    _, first_tokens = sketch_sequence("AAAAAA", config)
    _, second_tokens = sketch_sequence("CCCCCC", config)
    assert fingerprint_jaccard(first_tokens, second_tokens) == 0.0
