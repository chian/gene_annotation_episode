"""Kernel arithmetic and frozen protease parity; no new fit or native work.

Constructed matrices are numerical engineering controls. The opt-in retained
case compares current output with the byte-pinned pre-extraction source;
the original native239 artifact remains a separate immutable observation.
"""
from copy import deepcopy
from fractions import Fraction
import math

import pytest

from gene_annotation_episode import bivariate_covariance as kernel
from gene_annotation_episode import protease_kinetics_measurements as protease


@pytest.mark.parametrize("matrix,symmetry,positive", [
    ([[4., 1.], [1., 1.]], "exact", True),
    ([[4., 7.], [-5., 1.]], "asymmetric", True),
    ([[1., 1.], [1., 1.]], "exact", True),
    ([[0., 0.], [0., 0.]], "exact", True),
    ([[1e308, 0.], [0., 1e308]], "exact", True),
    ([[5e-324, 0.], [0., 5e-324]], "exact", True),
    ([[2**100, 0], [0, 1]], "exact", True),
    ([[1., 2.], [2., 1.]], "exact", False),
    ([[4., 6.], [2., 1.]], "asymmetric", False),
    ([[-1., 0.], [0., 1.]], "exact", False),
    ([[1., 1e308], [-1e308, 1.]], "asymmetric", True),
])
def test_exact_symmetric_part_assessment_preserves_original_entries(matrix, symmetry, positive):
    original = deepcopy(matrix)
    assert kernel.assess_bivariate_covariance(matrix) == {
        "status": "accepted" if positive else "symmetric_part_indefinite",
        "symmetry": symmetry, "symmetric_part_positive_semidefinite": positive}
    assert matrix == original


@pytest.mark.parametrize("matrix", [None, [], [1, 2], [[1]], [[1, 0], [0, 1], [0, 0]],
    ((1, 0), (0, 1)), [(1, 0), (0, 1)], {"matrix": [[1, 0], [0, 1]]}])
def test_shape_validation_precedes_fraction_arithmetic(monkeypatch, matrix):
    def forbidden(*args): raise AssertionError("invalid shape reached Fraction")
    monkeypatch.setattr(kernel, "Fraction", forbidden)
    assert kernel.assess_bivariate_covariance(matrix) == {"status": "shape_invalid",
        "symmetry": "unavailable", "symmetric_part_positive_semidefinite": None}


@pytest.mark.parametrize("entry", [True, "1", {"type": "nonfinite", "token": "inf"},
    float("nan"), float("inf"), -float("inf"), 2**53+1, 10**1000])
def test_finite_binary64_validation_precedes_fraction_arithmetic(monkeypatch, entry):
    matrix = [[entry, 0], [0, 1]]
    before = repr(matrix)
    def forbidden(*args): raise AssertionError("invalid numeric entry reached Fraction")
    monkeypatch.setattr(kernel, "Fraction", forbidden)
    assert kernel.assess_bivariate_covariance(matrix) == {"status": "entry_not_finite_binary64",
        "symmetry": "unavailable", "symmetric_part_positive_semidefinite": None}
    assert repr(matrix) == before


@pytest.mark.parametrize("gradient,matrix,expected", [
    ([Fraction(1, 3), Fraction(-4, 3)], [[4., 1.], [1., 1.]], Fraction(4, 3)),
    ([Fraction(1, 3), Fraction(-4, 3)], [[4., 7.], [-5., 1.]], Fraction(4, 3)),
    ([Fraction(1), Fraction(-1)], [[1., 1.], [1., 1.]], Fraction(0)),
    ([Fraction(0), Fraction(0)], [[5e-324, 0.], [0., 5e-324]], Fraction(0)),
    ([Fraction(1), Fraction(2)], [[1., 0.], [0., 1.]], Fraction(5)),
    ([Fraction(10**100), Fraction(10**100)], [[1., 1e308], [-1e308, 1.]], Fraction(2*10**200)),
])
def test_quadratic_form_retains_cross_terms_exact_cancellation_and_true_zero(gradient, matrix, expected):
    original = deepcopy((gradient, matrix))
    value = kernel.propagate_bivariate_variance(gradient, matrix)
    assert value == {"status": "present", "variance": float(expected),
        "standard_uncertainty": math.sqrt(float(expected))}
    assert (gradient, matrix) == original


@pytest.mark.parametrize("gradient,matrix,status", [
    ([Fraction(1), Fraction(-1)], [[1., 2.], [2., 1.]], "negative"),
    ([Fraction(10**200), Fraction(0)], [[1., 0.], [0., 0.]], "overflow"),
    ([Fraction(1, 10**200), Fraction(0)], [[1., 0.], [0., 0.]], "positive_underflow"),
])
def test_variance_range_failures_do_not_become_zero(gradient, matrix, status):
    assert kernel.propagate_bivariate_variance(gradient, matrix) == {
        "status": status, "variance": None, "standard_uncertainty": None}


@pytest.mark.parametrize("gradient,matrix,error", [
    ([], [[1., 0.], [0., 1.]], IndexError),
    ([object(), Fraction(0)], [[1., 0.], [0., 1.]], TypeError),
])
def test_programming_shape_and_type_errors_are_not_hidden(gradient, matrix, error):
    with pytest.raises(error):
        kernel.propagate_bivariate_variance(gradient, matrix)


