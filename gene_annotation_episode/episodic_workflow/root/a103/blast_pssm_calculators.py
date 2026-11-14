"""Deterministic numerical views of retained BLAST PSSM input sheets.

Matrices are positions x residue rows. No PSSM is constructed, no scores are
scaled, and native model quantities are never annotation probabilities.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import math

from .blast_pssm_master_inputs import (
    _STDAA, _add, _bad_field, _dimension, _master, _protein, _validate_sheet,
)


# seqport_util.cpp code tables, pinned source commit recorded in definitions.
_NCBI4NA = "-ACMGRSVTWYHKDBN"
_MATRICES = {"scores": ("finalData", "integer"), "resFreqsPerPos": ("intermediateData", "integer"),
             "weightedResFreqsPerPos": ("intermediateData", "real"), "freqRatios": ("intermediateData", "real")}
_VECTORS = {"informationContent": "real", "gaplessColumnWeights": "real", "sigma": "real",
            "intervalSizes": "integer", "numMatchingSeqs": "integer", "numIndeptObsr": "real"}
_STATISTICS = ("lambda", "kappa", "h", "scalingFactor", "lambdaUngapped", "kappaUngapped",
               "hUngapped", "wordScoreThreshold")


def _definition(source, formula, units, population, missingness, identity):
    return {"source": source, "formula": formula, "units": units, "population": population,
            "missingness": missingness, "identity": identity, "uncertainty": "not supplied by this format"}


def _definitions():
    result = {
        "source_version": "NCBI scoremat.asn and seqport_util.cpp at d4d56d4aa4fe16964e54c8c101fb1ec631ec6c05",
        "coordinates": "Zero-based positions and residue-row indices; master mapping is not a target-subject identification.",
        "defaults": "ASN defaults only: absent isProtein=true; absent byRow=false; absent finalData.scalingFactor=1 only when finalData is present. Reported presence remains in the sheet.",
        "real_decoder": "Native REAL {mantissa,base,exponent} means mantissa*base**exponent, base 2 or 10. Decimal base 10 and exact Fraction base 2 are converted once to finite binary64. Decimal literals retain their token. Nonzero values rounding to zero and nonfinite/overflow values are unavailable with an issue, never measured zero.",
        "array_status": "Every defined matrix/vector native path is available, unavailable (absent or unrepresentable), or incompatible (type, cardinality, dimensions or storage order). One bad array does not suppress valid siblings.",
        "status": "Complete means the represented arrays and master mapping are decoded with no issues; absent optional sibling arrays/diagnostics need not exist. Partial preserves available matrices when any required mapping/value is absent or incompatible. No available matrix yields unavailable, or incompatible for invalid syntax/types/geometry.",
        "no_combination": "Components are retained individually. No sum, probability, annotation confidence, generated sequence, family prevalence or statistical uncertainty is inferred.",
    }
    reshape = "For M=numRows,N=numColumns: output[p][r]=input[r*N+p] if effective byRow, else input[p*M+r]; require M*N values. No division by scalingFactor."
    missing = "Absent is null/unavailable; wrong length/type is null/incompatible; unrepresentable REAL is null/unavailable. Original array remains in sheet."
    meanings = {
        "scores": ("native integer model score", "Native final PSSM score, including negative and sentinel-like values"),
        "resFreqsPerPos": ("native integer residue frequency/count", "Observed residue frequencies or counts before pseudocounts; exact convention is the native producer's"),
        "weightedResFreqsPerPos": ("dimensionless native weight", "Weighted observed residue frequencies, f_i in the scoremat schema reference; not renormalized"),
        "freqRatios": ("dimensionless native frequency ratio", "PSSM frequency ratios; not probabilities or independently observed population prevalence"),
    }
    for name, (parent, _) in _MATRICES.items():
        units, identity = meanings[name]
        result["matrix_values." + name] = _definition("pssm." + parent + "." + name, reshape, units,
            "Each model position and alphabet row; no external biological-population denominator", missing, identity)
    vectors = {
        "informationContent": ("native information-content units (unit not declared in scoremat.asn)", "Model information content per position"),
        "gaplessColumnWeights": ("dimensionless relative weight", "Relative column weight without gaps to pseudocounts"),
        "sigma": ("native sequence-weighting diagnostic (units not declared)", "Native value used in sequence-weights computation"),
        "intervalSizes": ("aligned-region length", "Length of aligned regions per query position"),
        "numMatchingSeqs": ("sequence count", "Number of matching sequences including the query"),
        "numIndeptObsr": ("native effective observation count", "Number of independent observations used by the native model; not independent biological replicates"),
    }
    for name, (units, identity) in vectors.items():
        result["position_diagnostics." + name] = _definition("pssm.intermediateData." + name,
            "Copy N values in native position order; decode REAL without normalization.", units,
            "One value per model position; producer's alignment population", missing, identity)
    for name in _STATISTICS:
        units = ("native integer score multiplier" if name == "scalingFactor" else
                 "native word-score units" if name == "wordScoreThreshold" else
                 "inverse native score units" if name.startswith("lambda") else "native dimensionless model parameter")
        result["native_statistics." + name] = _definition("pssm.finalData." + name,
            "Exact integer copy or native REAL decode; scalingFactor alone defaults to 1 within present finalData.",
            units, "The retained PSSM's native statistical model, not annotation correctness",
            "Absent optional statistic is null; absent required lambda/kappa/h issues; invalid or unrepresentable is null.",
            "Native model statistic; no recalibration")
    result["dimensions"] = _definition("pssm.numRows,pssm.numColumns", "Copy positive integers M,N.",
        "residue rows, model positions", "One retained model", "Missing/invalid dimension is null; dependent matrix unavailable.", "Native dimensions")
    result["residue_alphabet"] = _definition("pssm.rowLabels,isProtein,numRows",
        "Use M supplied string labels; only when rowLabels is absent use protein code indices 0..25 or 0..27, or nucleotide 0..15, from native tables.",
        "symbol labels", "M native matrix rows, no resorting", "Invalid supplied labels or unsupported unlabelled dimensions retain matrix indices but labels are null.", "Native label correspondence")
    result["master"] = _definition("pssm.query.seq.inst.{repr,mol,length,seq-data},pssm.numColumns",
        "Decode supported exact protein codes; verify declared length=decoded length=N; retain native column p and symbol. master_position is null for '-', otherwise p; later native positions are not renumbered. This differs from the CLUSTAL ungapped-master map.",
        "residues; zero-based coordinates", "The explicit single master Seq-entry only",
        "Missing, compound or unsupported master leaves mapping null; length mismatch retains decoded sequence but map is null.",
        "Decoded supplied master, not model-generated consensus or target-subject sequence")
    result["native_parameters"] = _definition("PssmWithParameters.params",
        "Retain supplied parameters including native REAL representations; no current executable defaults.",
        "Native parameter-specific units", "The retained PSSM construction parameters",
        "Absent is null; uninterpreted supplied fields remain supplied.", "Native supplied model parameters, unused in these numerical views")
    return result


class _Number(ValueError):
    pass


def _real(value):
    """Decode ASN REAL exactly before one binary64 rounding; never underflow to 0."""
    try:
        if type(value) is int:
            exact = value
        elif type(value) is float:
            exact = value
        elif type(value) is list and len(value) == 3 and all(type(v) is int for v in value):
            mantissa, base, exponent = value
            if base not in {2, 10}:
                raise _Number("real_invalid")
            if not mantissa:
                return 0.0
            if base == 10:
                digits = tuple(int(d) for d in str(abs(mantissa)))
                exact = Decimal((int(mantissa < 0), digits, exponent))
            else:
                bits = abs(mantissa).bit_length() + exponent
                if bits > 1024:
                    raise _Number("real_unrepresentable")
                if bits < -1074:
                    raise _Number("real_underflow")
                exact = Fraction(mantissa << exponent) if exponent >= 0 else Fraction(mantissa, 1 << -exponent)
        elif type(value) is dict and set(value) == {"real_token"} and type(value["real_token"]) is str:
            exact = Decimal(value["real_token"])
        elif value in ("PLUS-INFINITY", "MINUS-INFINITY", "NOT-A-NUMBER", "NaN", "Infinity", "-Infinity"):
            raise _Number("real_nonfinite")
        else:
            raise _Number("real_invalid")
        if isinstance(exact, Decimal) and not exact.is_finite() or type(exact) is float and not math.isfinite(exact):
            raise _Number("real_nonfinite")
        number = float(exact)
        if not math.isfinite(number):
            raise _Number("real_unrepresentable")
        if exact != 0 and number == 0:
            raise _Number("real_underflow")
        return number
    except (OverflowError, InvalidOperation):
        raise _Number("real_unrepresentable") from None
    except (TypeError, ValueError) as error:
        if isinstance(error, _Number):
            raise
        raise _Number("real_invalid") from None


def _number(value, kind):
    if kind == "integer":
        if type(value) is not int:
            raise _Number("integer_invalid")
        return value
    return _real(value)


def _array(row, result, parent, name, kind, length, *, rows=None, by_row=None):
    path = "pssm." + parent + "." + name
    data = row["native_pssm"].get(parent)
    if _bad_field(row, path):
        result["array_status"][path] = "incompatible"
        _add(row, result["issues"], "array_type_invalid", path)
        return None
    if not isinstance(data, dict) or name not in data:
        result["array_status"][path] = "unavailable"
        return None
    source = data[name]
    if type(source) is not list:
        result["array_status"][path] = "incompatible"
        _add(row, result["issues"], "array_type_invalid", path)
        return None
    if length is None or rows is not None and by_row is None:
        result["array_status"][path] = "incompatible"
        _add(row, result["issues"], "array_order_unavailable" if rows is not None and by_row is None else "dimensions_invalid", path)
        return None
    if len(source) != length:
        result["array_status"][path] = "incompatible"
        _add(row, result["issues"], "array_length_incompatible", path)
        return None
    decoded, failures = [], []
    for index, value in enumerate(source):
        try:
            decoded.append(_number(value, kind))
        except _Number as error:
            failures.append(str(error))
            _add(row, result["issues"], str(error), f"{path}[{index}]")
    if failures:
        result["array_status"][path] = "incompatible" if any(f in {"integer_invalid", "real_invalid"} for f in failures) else "unavailable"
        return None
    result["array_status"][path] = "available"
    if rows is None:
        return decoded
    positions = length // rows
    return [[decoded[r * positions + p if by_row else p * rows + r] for r in range(rows)]
            for p in range(positions)]


def _components(row):
    pssm, issues = row["native_pssm"], deepcopy(row["issues"])
    dimensions = {}
    for native, derived in (("numRows", "residue_rows"), ("numColumns", "positions")):
        dimensions[derived] = _dimension(row, native)
        if dimensions[derived] is None:
            _add(row, issues, "dimensions_invalid", "pssm." + native)
    is_protein = _protein(row)
    order = pssm.get("byRow", False)
    if type(order) is not bool or _bad_field(row, "pssm.byRow"):
        order = None
    result = {"pssm_key": row["pssm_key"], "record_ordinal": row["record_ordinal"], "status": "unavailable",
        "dimensions": dimensions, "is_protein": is_protein,
        "native_order": {"reported_by_row": pssm.get("byRow") if type(pssm.get("byRow")) is bool else None, "effective_by_row": order},
        "residue_alphabet": None, "alphabet_source": None,
        "matrix_values": {}, "position_diagnostics": {}, "native_statistics": {},
        "native_parameters": deepcopy(row["native_params"]), "master": None, "array_status": {}, "issues": issues}
    rows, columns = dimensions["residue_rows"], dimensions["positions"]
    labels = pssm.get("rowLabels")
    if "rowLabels" in pssm and type(labels) is list and len(labels) == rows and all(type(v) is str for v in labels) and not _bad_field(row, "pssm.rowLabels"):
        result.update(residue_alphabet=deepcopy(labels), alphabet_source="rowLabels")
    elif "rowLabels" in pssm:
        _add(row, issues, "row_labels_incompatible", "pssm.rowLabels")
    else:
        if is_protein is True and rows in {26, 28}:
            result.update(residue_alphabet=list(_STDAA[:rows]), alphabet_source="ncbistdaa")
        elif is_protein is False and rows == 16:
            result.update(residue_alphabet=list(_NCBI4NA), alphabet_source="ncbi4na")
        else:
            _add(row, issues, "alphabet_unavailable", "pssm.numRows")
    cardinality = rows * columns if rows is not None and columns is not None else None
    for name, (parent, kind) in _MATRICES.items():
        result["matrix_values"][name] = _array(row, result, parent, name, kind, cardinality,
                                               rows=rows, by_row=order)
    for name, kind in _VECTORS.items():
        result["position_diagnostics"][name] = _array(row, result, "intermediateData", name, kind, columns)
    final = pssm.get("finalData")
    for name in _STATISTICS:
        path = "pssm.finalData." + name
        number = None
        if type(final) is dict and not _bad_field(row, "pssm.finalData"):
            if name not in final and name == "scalingFactor":
                number = 1
            elif name in final and not _bad_field(row, path):
                try:
                    number = _number(final[name], "integer" if name == "scalingFactor" else "real")
                except _Number as error:
                    _add(row, issues, str(error), path)
            elif name in {"lambda", "kappa", "h"}:
                _add(row, issues, "statistic_missing", path)
        result["native_statistics"][name] = number
    result["master"] = _master(row, result, columns, is_protein)
    available = any(v is not None for v in result["matrix_values"].values())
    if available:
        result["status"] = "partial" if issues else "complete"
    else:
        incompatible = any(v == "incompatible" for v in result["array_status"].values()) or any(
            i["code"] in {"dimensions_invalid", "asn_syntax_invalid", "asn_truncated", "asn_duplicate_field", "asn_field_type_invalid"} for i in issues)
        result["status"] = "incompatible" if incompatible else "unavailable"
        if all(v == "unavailable" for v in result["array_status"].values()):
            _add(row, issues, "array_missing", "pssm")
    return result


def calculate_blast_pssm_components(sheet: dict) -> dict:
    """Recalculate only from finite saved JSON; no filesystem or process calls."""
    _validate_sheet(sheet)
    matrices = [_components(row) for row in sheet["pssms"]]
    issues = deepcopy(sheet["issues"])
    for matrix in matrices:
        for problem in matrix["issues"]:
            if problem not in issues:
                issues.append(deepcopy(problem))
    if matrices and all(m["status"] == "complete" for m in matrices) and not issues:
        status = "complete"
    elif any(m["status"] in {"complete", "partial"} for m in matrices):
        status = "partial"
    elif any(m["status"] == "incompatible" for m in matrices) or sheet["status"] == "incompatible":
        status = "incompatible"
    else:
        status = "unavailable"
    return {"schema": "blast_pssm_components_v1", "status": status, "matrices": matrices,
            "issues": issues, "definitions": _definitions()}


__all__ = ["calculate_blast_pssm_components"]
