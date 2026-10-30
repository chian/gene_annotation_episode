"""Neutral arithmetic for a retained two-variable matrix and quadratic form.

These functions assess supplied numeric entries, without establishing their
statistical validity. Callers own parameter names, physical units, source
custody and the policy for using an asymmetric reported matrix.
"""
from __future__ import annotations

from fractions import Fraction
import math
from typing import Literal, TypedDict


class BivariateCovarianceAssessment(TypedDict):
    status: Literal["accepted", "shape_invalid", "entry_not_finite_binary64", "symmetric_part_indefinite"]
    symmetry: Literal["exact", "asymmetric", "unavailable"]
    symmetric_part_positive_semidefinite: bool | None


class BivariateVariance(TypedDict):
    status: Literal["present", "negative", "overflow", "positive_underflow", "numerical_range"]
    variance: float | None
    standard_uncertainty: float | None


def _finite_binary64(value):
    if type(value) not in (int, float):
        return False
    try:
        result = float(value)
    except OverflowError:
        return False
    return math.isfinite(result) and (type(value) is not int or result == value)


def assess_bivariate_covariance(value) -> BivariateCovarianceAssessment:
    """Assess the exact symmetric bilinear part, preserving the supplied matrix.

    A finite entry must retain its value in binary64. Shape and numeric checks
    precede Fraction conversion. Positive semidefiniteness of this two-variable
    form neither authenticates a covariance estimate nor assesses a larger
    matrix from which these entries might have been selected.
    """
    result: BivariateCovarianceAssessment = {"status": "shape_invalid", "symmetry": "unavailable",
        "symmetric_part_positive_semidefinite": None}
    if type(value) is not list or len(value) != 2 or any(type(row) is not list or len(row) != 2 for row in value):
        return result
    if any(not _finite_binary64(entry) for row in value for entry in row):
        result["status"] = "entry_not_finite_binary64"
        return result
    result["symmetry"] = "exact" if value[0][1] == value[1][0] else "asymmetric"
    a, c = Fraction(value[0][0]), Fraction(value[1][1])
    b = (Fraction(value[0][1]) + Fraction(value[1][0])) / 2
    if a < 0 or c < 0 or a*c < b*b:
        result.update(status="symmetric_part_indefinite", symmetric_part_positive_semidefinite=False)
        return result
    result.update(status="accepted", symmetric_part_positive_semidefinite=True)
    return result


def propagate_bivariate_variance(gradient: tuple[Fraction, Fraction] | list[Fraction],
        matrix: list[list[int | float]]) -> BivariateVariance:
    """Evaluate one two-variable quadratic form in the original exact order.

    Callers supply a compatible two-entry gradient and finite matrix, and own
    their assessment policy. The skew-symmetric part cancels algebraically;
    no rounded replacement matrix is constructed. Data-range failures remain
    distinct from an exact zero. Programming shape/type failures are not hidden.
    """
    def unavailable(status) -> BivariateVariance:
        return {"status": status, "variance": None, "standard_uncertainty": None}

    try:
        exact = sum((gradient[i] * Fraction(matrix[i][j]) * gradient[j]
            for i in range(2) for j in range(2)), Fraction(0))
        if exact < 0:
            return unavailable("negative")
        variance = float(exact)
        if not math.isfinite(variance):
            return unavailable("overflow")
        if exact > 0 and variance == 0:
            return unavailable("positive_underflow")
        return {"status": "present", "variance": variance,
            "standard_uncertainty": math.sqrt(variance)}
    except OverflowError:
        return unavailable("overflow")
    except (ArithmeticError, ValueError):
        return unavailable("numerical_range")


__all__ = ["BivariateCovarianceAssessment", "BivariateVariance",
    "assess_bivariate_covariance", "propagate_bivariate_variance"]
