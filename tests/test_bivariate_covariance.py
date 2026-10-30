"""Kernel arithmetic and frozen protease parity; no new fit or native work.

Constructed matrices are numerical engineering controls. The opt-in retained
case compares current-v2 output with the byte-pinned pre-extraction source;
the original native239 v1 artifact remains a separate immutable observation.
"""
from copy import deepcopy
from fractions import Fraction
import builtins
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

import pytest

from gene_annotation_episode import bivariate_covariance as kernel
from gene_annotation_episode import protease_kinetics_measurements as protease
from test_protease_kinetics_measurements import supplied_fixture


_BASELINE_SHA = "e5fa57e6aa06a2b3a27da9866455bd9626b52deee33f0043074d0ac7b321df78"
_SHEET_SHA = "5ce86df48853601e7d05472f30fcfef148116ad9031f5c4035d5f10f114a5765"
_ORIGINAL_COMPONENTS_SHA = "5bdacd46a9105c07e9d855ce993332e4a8eef2838dbd7f2526036db916f589c4"


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


@pytest.fixture(scope="module")
def frozen_protease():
    filename = os.environ.get("HMMER_NATIVE_ORACLE_BIVARIATE_PROTEASE_BASELINE")
    if filename is None:
        pytest.skip("engineering parity requires the explicitly selected frozen pre-extraction source")
    path = Path(filename)
    raw = path.read_bytes()
    assert len(raw) == 38101 and hashlib.sha256(raw).hexdigest() == _BASELINE_SHA
    name = "protease_pre_bivariate_extraction_engineering"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    yield module
    assert path.read_bytes() == raw


def matrix_case(kind):
    return deepcopy({"symmetric": [[4., 1.], [1., 1.]], "asymmetric": [[4., 7.], [-5., 1.]],
        "singular": [[1., 1.], [1., 1.]], "zero": [[0., 0.], [0., 0.]],
        "indefinite": [[1., 2.], [2., 1.]],
        "nonfinite": [[{"type": "nonfinite", "token": "inf"}, 0], [0, 1]],
        "bool": [[True, 0], [0, 1]], "unrepresentable": [[2**53+1, 0], [0, 1]],
        "shape": [[1]], "underflow": [[5e-324, 0.], [0., 0.]]}[kind])


@pytest.mark.parametrize("kind", ["symmetric", "asymmetric", "singular", "zero", "indefinite",
    "nonfinite", "bool", "unrepresentable", "shape", "underflow"])
def test_protease_wrappers_preserve_exact_frozen_metadata_and_full_v2_components(frozen_protease, kind):
    raw = matrix_case(kind)
    before = deepcopy(raw)
    original, current = frozen_protease._covariance(raw), protease._covariance(raw)
    assert current == original and raw == before
    if current[0] is not None:
        assert current[0] is original[0] is raw
    gradient = [Fraction(1, 3), Fraction(-4, 3)]
    assert protease._uncertainty(gradient, *current) == frozen_protease._uncertainty(gradient, *original)
    measurements, capture, context = supplied_fixture()
    capture["observer"]["locals"]["covariance"] = raw
    sheet = protease.populate_protease_kinetics_sheet(measurements=measurements,
        native_capture=capture, assay_context=context)
    expected = frozen_protease.calculate_protease_kinetics_components(sheet)
    actual = protease.calculate_protease_kinetics_components(sheet)
    assert json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)
    assert actual["schema"] == "protease_kinetics_components_v2"
    assert actual["fit_components"]["vmax"]["value"] == 12


@pytest.mark.parametrize("gradient,matrix", [
    ([Fraction(1), Fraction(-1)], [[1., 2.], [2., 1.]]),
    ([Fraction(10**200), Fraction(0)], [[1., 0.], [0., 0.]]),
    ([Fraction(1, 10**200), Fraction(0)], [[1., 0.], [0., 0.]]),
    ([Fraction(1), Fraction(0)], [["invalid_numeric", 0], [0, 1]]),
])
def test_protease_arithmetic_failure_translation_stays_exact(frozen_protease, gradient, matrix):
    # These direct private-adapter controls test failure classification, not
    # scientific admission of an indefinite or malformed covariance matrix.
    _, _, assessment = frozen_protease._covariance([[1., 0.], [0., 1.]])
    assert protease._uncertainty(gradient, matrix, None, assessment) == frozen_protease._uncertainty(
        gradient, matrix, None, assessment)


def test_authentic239_saved_v2_output_matches_frozen_source_and_preserves_distinct_original_v1(frozen_protease, monkeypatch):
    sheet_name = os.environ.get("HMMER_NATIVE_ORACLE_PROTEASE_RETAINED_SHEET")
    original_name = os.environ.get("HMMER_NATIVE_ORACLE_PROTEASE_RETAINED_COMPONENTS")
    if sheet_name is None or original_name is None:
        pytest.skip("saved239 parity requires both explicitly selected original artifacts")
    paths = [Path(sheet_name), Path(original_name)]
    before = [path.read_bytes() for path in paths]
    assert len(before[0]) == 394094 and hashlib.sha256(before[0]).hexdigest() == _SHEET_SHA
    assert len(before[1]) == 15229 and hashlib.sha256(before[1]).hexdigest() == _ORIGINAL_COMPONENTS_SHA
    sheet, original = map(json.loads, before)
    sheet_before = deepcopy(sheet)
    actual_import = builtins.__import__
    def no_fitting(name, *args, **kwargs):
        if name.split(".")[0] in {"biomni", "scipy", "numpy", "matplotlib"}:
            raise AssertionError("saved covariance parity imported a fitting library")
        return actual_import(name, *args, **kwargs)
    def no_io(*args, **kwargs):
        raise AssertionError("saved covariance parity attempted external work")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "__import__", no_fitting)
        patch.setattr(builtins, "open", no_io)
        patch.setattr(Path, "open", no_io)
        patch.setattr(os, "open", no_io)
        expected = frozen_protease.calculate_protease_kinetics_components(sheet)
        actual = protease.calculate_protease_kinetics_components(sheet)
    assert sheet == sheet_before
    assert json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)
    assert actual["schema"] == expected["schema"] == "protease_kinetics_components_v2"
    assert original["schema"] == "protease_kinetics_components_v1"
    assert original["native_values"]["covariance"] == actual["native_values"]["covariance"]
    assert original["native_values"]["params"] == actual["native_values"]["params"]
    assert [path.read_bytes() for path in paths] == before
