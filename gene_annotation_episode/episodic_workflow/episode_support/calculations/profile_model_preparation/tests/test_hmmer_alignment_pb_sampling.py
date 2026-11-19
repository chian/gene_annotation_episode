"""Source-derived sampler fixtures; these are not captured native outputs.

Scripted double streams below are hand traces of retained esl_rand64.c. Actual
MT19937-64/Deal conformance belongs to the separately recorded native diagnostic
run; no native program is launched by these tests.
"""
from __future__ import annotations

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.calculations.profile_model_preparation import hmmer_alignment_pb_sampling as sampling


@pytest.mark.parametrize("seed", [1, 42, (1 << 64) - 1])
@pytest.mark.parametrize("size", [1, 2, 3, 17, 312, 313])
def test_full_sample_preserves_every_ordinal(size, seed):
    assert sampling.sample_easel_pb_rows(size, sample_size=size, seed=seed) == list(range(size))


@pytest.mark.parametrize("value,expected", [
    (0.0, 0.0), (.499, 0.0), (.5, 1.0), (1.5, 2.0),
    (2.5, 3.0), (float((1 << 52) - 1), float((1 << 52) - 1)),
])
def test_c_round_is_away_from_zero_without_add_half_loss(value, expected):
    assert sampling._round_nonnegative(value) == expected


@pytest.mark.parametrize("field", ["population_size", "sample_size", "seed"])
@pytest.mark.parametrize("bad", [True, False, 1.0, "1", None, [], {}])
def test_noninteger_settings_are_rejected(field, bad):
    values = {"population_size": 100, "sample_size": 10, "seed": 42}
    values[field] = bad
    with pytest.raises(ValueError, match="^settings_invalid$"):
        sampling.sample_easel_pb_rows(**values)


@pytest.mark.parametrize("population_size,sample_size,seed", [
    (0, 0, 42), (10, 0, 42), (0, 1, 42), (-1, 1, 42),
    (10, -1, 42), (10, 11, 42), (10, 1, 0), (10, 1, -1),
    (1 << 63, 1, 42), (10, 1 << 63, 42), (10, 1, 1 << 64),
    ((1 << 63) - 1, ((1 << 63) - 1) // 13 + 1, 42),
])
def test_native_domain_violations_are_rejected(population_size, sample_size, seed):
    with pytest.raises(ValueError, match="^settings_invalid$"):
        sampling.sample_easel_pb_rows(population_size, sample_size=sample_size, seed=seed)


def test_largest_defined_integer_setup_is_validated_without_allocating_sample():
    sampling._validate_settings(
        (1 << 63) - 1, ((1 << 63) - 1) // 13, (1 << 64) - 1
    )


def test_invalid_settings_are_rejected_before_rng_creation(monkeypatch):
    def forbidden(seed):
        raise AssertionError("RNG was created for invalid settings")

    monkeypatch.setattr(sampling, "_EaselMT19937_64", forbidden)
    with pytest.raises(ValueError, match="^settings_invalid$"):
        sampling.sample_easel_pb_rows(10, sample_size=0, seed=42)
