"""Deterministic numerical views of retained BLAST PSSM input sheets.

Matrices are positions x residue rows. No PSSM is constructed, no scores are
scaled, and native model quantities are never annotation probabilities.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
import math
import re

from .blast_pssm_inputs import ISSUE_CODES, _issue


# seqport_util.cpp code tables, pinned source commit recorded in definitions.
_STDAA = "-ABCDEFGHIKLMNPQRSTVWXYZU*OJ"
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


def _finite_json(value):
    if type(value) is dict:
        return all(type(k) is str and _finite_json(v) for k, v in value.items())
    if type(value) is list:
        return all(_finite_json(v) for v in value)
    return value is None or type(value) in {str, int, bool} or type(value) is float and math.isfinite(value)


def _validate_sheet(sheet):
    keys = {"schema", "artifact_key", "source_ref", "format", "input_identity", "status", "native_text", "pssms", "issues"}
    records = {"record_ordinal", "pssm_key", "character_span", "native_type", "native_record", "native_pssm", "native_params", "issues"}
    if not _finite_json(sheet) or type(sheet) is not dict or set(sheet) != keys or sheet["schema"] != "blast_pssm_sheet_v1":
        raise ValueError("blast_pssm_sheet_invalid")
    if type(sheet["pssms"]) is not list or type(sheet["issues"]) is not list:
        raise ValueError("blast_pssm_sheet_invalid")
    seen = set()
    for row in sheet["pssms"]:
        if type(row) is not dict or set(row) != records or type(row["native_pssm"]) is not dict:
            raise ValueError("blast_pssm_record_invalid")
        ordinal = row["record_ordinal"]
        if type(ordinal) is not int or ordinal < 0 or ordinal in seen:
            raise ValueError("blast_pssm_record_identity_invalid")
        seen.add(ordinal)
        if row["pssm_key"] != json.dumps([sheet["artifact_key"], ordinal], ensure_ascii=False, separators=(",", ":")):
            raise ValueError("blast_pssm_record_identity_invalid")
        if type(row["native_record"]) is not dict or row["native_params"] is not None and type(row["native_params"]) is not dict:
            raise ValueError("blast_pssm_record_invalid")
        if type(row["issues"]) is not list or any(type(i) is not dict or i.get("code") not in ISSUE_CODES for i in row["issues"]):
            raise ValueError("blast_pssm_record_issues_invalid")


def _node_at(row, path):
    parts = re.findall(r"[^.\[\]]+", path)
    if row["native_type"] == "Pssm" and parts[:1] == ["pssm"]:
        parts.pop(0)
    node = row["native_record"]
    for part in parts:
        if node.get("kind") == "choice":
            if node.get("name") != part:
                return None
            node = node["value"]
        elif node.get("kind") == "group":
            if part.isdigit():
                items = node.get("items", [])
                if int(part) >= len(items):
                    return None
                node = items[int(part)]
            else:
                found = [v for v in node.get("items", []) if v.get("kind") == "choice" and v.get("name") == part]
                if len(found) != 1:
                    return None
                node = found[0]["value"]
        else:
            return None
    return node


def _add(row, issues, code, path):
    node = _node_at(row, path)
    issues.append(_issue(code, row["record_ordinal"], path,
                         node.get("character_span") if node is not None else None))


def _bad_field(row, path):
    # A malformed ancestor blocks its descendants, while independent siblings
    # survive. A truncated outer record alone does not erase complete arrays.
    for issue in row["issues"]:
        field = issue.get("field")
        if issue["code"] in {"asn_duplicate_field", "asn_field_type_invalid", "asn_field_truncated"} and field:
            if path == field or path.startswith(field + ".") or path.startswith(field + "["):
                return True
    return False


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


def _plain_fields(value):
    if type(value) is not list or any(type(v) is not dict or len(v) != 1 for v in value):
        return None
    names = [next(iter(v)) for v in value]
    if len(set(names)) != len(names):
        return None
    return {k: v for item in value for k, v in item.items()}


def _master(row, result, columns, is_protein):
    master = {"status": "unavailable", "encoding": None, "reported_length": None,
              "decoded_length": None, "sequence": None, "column_to_residue": None}
    pssm, path = row["native_pssm"], "pssm.query"
    def fail(code, field=path, state="incompatible"):
        master["status"] = state
        _add(row, result["issues"], code, field)
        return master
    if "query" not in pssm:
        return fail("master_missing", state="unavailable")
    query = pssm["query"]
    if _bad_field(row, path) or type(query) is not dict or len(query) != 1:
        return fail("master_shape_invalid")
    if "set" in query:
        return fail("master_compound_unsupported", state="unavailable")
    if "seq" not in query:
        return fail("master_shape_invalid")
    seq = _plain_fields(query["seq"])
    inst = _plain_fields(seq.get("inst")) if seq is not None else None
    if inst is None or _bad_field(row, path + ".seq.inst"):
        return fail("master_shape_invalid", path + ".seq.inst")
    path += ".seq.inst"
    length = inst.get("length")
    if type(length) is int and length >= 0:
        master["reported_length"] = length
    if "repr" in inst and inst["repr"] != "raw":
        return fail("master_representation_unsupported", path + ".repr", "unavailable")
    if is_protein is not True or "mol" in inst and inst["mol"] != "aa":
        return fail("master_molecule_incompatible", path + ".mol")
    data = inst.get("seq-data")
    if type(data) is not dict or len(data) != 1:
        return fail("master_shape_invalid", path + ".seq-data")
    encoding, encoded = next(iter(data.items()))
    master["encoding"] = encoding
    if encoding == "ncbistdaa":
        if type(encoded) is not dict or encoded.get("encoding") != "hex" or type(encoded.get("token")) is not str:
            return fail("master_encoding_unsupported", path + ".seq-data", "unavailable")
        token = encoded["token"]
        if re.fullmatch(r"'[0-9A-Fa-f\s]*'[Hh]", token) is None:
            return fail("master_code_invalid", path + ".seq-data")
        try:
            codes = bytes.fromhex(token[1:-2])
        except ValueError:
            return fail("master_code_invalid", path + ".seq-data")
        if any(code >= len(_STDAA) for code in codes):
            return fail("master_code_invalid", path + ".seq-data")
        sequence = "".join(_STDAA[code] for code in codes)
    elif encoding in {"iupacaa", "ncbieaa"}:
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ" + ("-*" if encoding == "ncbieaa" else ""))
        if type(encoded) is not str or not set(encoded) <= allowed:
            return fail("master_code_invalid", path + ".seq-data")
        sequence = encoded
    else:
        return fail("master_encoding_unsupported", path + ".seq-data", "unavailable")
    master.update(sequence=sequence, decoded_length=len(sequence))
    if master["reported_length"] is None:
        return fail("master_length_missing", path + ".length", "unavailable")
    if _bad_field(row, path + ".length") or len(sequence) != length or columns != length:
        return fail("master_length_incompatible", path + ".length")
    master.update(status="complete", column_to_residue=[
        {"column": p, "master_position": None if symbol == "-" else p, "symbol": symbol}
        for p, symbol in enumerate(sequence)])
    return master


def _components(row):
    pssm, issues = row["native_pssm"], deepcopy(row["issues"])
    dimensions = {}
    for native, derived in (("numRows", "residue_rows"), ("numColumns", "positions")):
        value = pssm.get(native)
        dimensions[derived] = value if type(value) is int and value > 0 and not _bad_field(row, "pssm." + native) else None
        if dimensions[derived] is None:
            _add(row, issues, "dimensions_invalid", "pssm." + native)
    is_protein = pssm.get("isProtein", True)
    if type(is_protein) is not bool or _bad_field(row, "pssm.isProtein"):
        is_protein = None
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
