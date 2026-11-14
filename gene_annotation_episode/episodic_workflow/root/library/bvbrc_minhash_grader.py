"""Pure readers and numerical components for the native BV-BRC Minhash result.

The input is the synchronous RPC's result[0], a list of four-field rows, not
an AppService task or a Mash TSV. Acquisition and receipt custody belong to
the caller. No function here performs I/O, chooses work, or assigns credit.

Native measurements and their types remain in ``native_result``/``native_row``.
The numerical cells are parsed values, not calibrated annotation probabilities.
Calculators use explicit pair metadata joined on BOTH row index and genome ID.
See verification/tool_graders_bvbrc_minhash_2026-10-24/README.md for numerical
meanings, missing-data behavior, pinned sources, and verification limitations.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import json
import math
import re

from scipy.special import expit, logsumexp
from scipy.stats import binom


SHEET_SCHEMA = "bvbrc_minhash_sheet_v1"
COMPONENTS_SCHEMA = "bvbrc_minhash_components_v1"
METHODS = {
    "genome": "Minhash.compute_genome_distance_for_genome2",
    "fasta": "Minhash.compute_genome_distance_for_fasta2",
}
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_COUNTS = re.compile(r"([0-9]+)/([0-9]+)\Z")
_METADATA_FIELDS = ("kmer_length", "query_length", "reference_length", "alphabet_size")

# Closed names of the existing parser/calculator diagnostics for typed returns.
MINHASH_DIAGNOSTIC_CODES = (
    'ambiguous_pair_metadata',
    'binomial_integer_precision_unsupported',
    'binomial_tail_unavailable',
    'counts_integer_conversion_unavailable',
    'distance_numeric_range_unsupported',
    'distance_saturated_at_one',
    'distance_underflow_or_rounding',
    'eight_native_arguments_required',
    'empty_result_completeness_unknown',
    'invalid_counts_token',
    'invalid_genome_id',
    'invalid_native_number',
    'kmer_space_overflow_log_calculation_used',
    'minhash_sheet_required',
    'missing_calculation_input',
    'missing_native_field',
    'native_integer_argument_required',
    'native_number_outside_unit_interval',
    'native_numeric_conversion_underflow',
    'native_request_object_required',
    'native_result_array_required',
    'native_row_arity',
    'native_row_array_required',
    'negative_native_number',
    'nonfinite_native_number',
    'null_model_numeric_range_unsupported',
    'null_native_field',
    'pair_metadata_array_required',
    'pair_metadata_genome_id_mismatch',
    'pair_metadata_missing',
    'pair_metadata_object_required',
    'pair_metadata_row_index_mismatch',
    'positive_integer_metadata_required',
    'query_identifier_required',
    'random_jaccard_rounded_to_one',
    'random_jaccard_underflow',
    'recomputed_pvalue_rounded_to_one',
    'recomputed_pvalue_underflow',
    'reported_pvalue_zero_precision_unknown',
    'request_method_mode_mismatch',
    'row_identity_unavailable',
    'shared_fraction_underflow_or_rounding',
    'shared_hashes_exceed_union',
    'sheet_native_row_count_mismatch',
    'sheet_native_row_mismatch',
    'structured_metadata_provenance_required',
    'structured_provenance_required',
    'unsupported_minhash_mode',
    'valid_hash_counts_required',
    'workspace_fasta_path_required',
    'zero_compared_union_hashes',
    'zero_union_calculations_unavailable',
)


def _issue(issues, code, path, *, severity="error"):
    issues.append({"code": code, "path": path, "severity": severity})


def _structured(value):
    if not isinstance(value, (dict, list)):
        return False
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError):
        return False
    return True


def _number(value, path, issues):
    """Read a nonnegative finite native number, preserving its raw value elsewhere."""
    if value is None:
        _issue(issues, "null_native_field", path)
        return None
    if type(value) not in (int, float, str):
        _issue(issues, "invalid_native_number", path)
        return None
    if isinstance(value, str):
        if not _NUMBER.fullmatch(value):
            _issue(issues, "invalid_native_number", path)
            return None
        number = float(value)
    else:
        number = value
    if isinstance(number, float) and not math.isfinite(number):
        _issue(issues, "nonfinite_native_number", path)
        return None
    if number < 0 or (isinstance(value, str) and Decimal(value) < 0):
        _issue(issues, "negative_native_number", path)
        return None
    if number > 1:
        _issue(issues, "native_number_outside_unit_interval", path)
        return None
    if isinstance(value, str) and number == 0 and Decimal(value) != 0:
        _issue(issues, "native_numeric_conversion_underflow", path, severity="warning")
    return number


def _read_row(native, index):
    issues = []
    prefix = f"native_result[{index}]"
    row = {"row_index": index, "genome_id": None, "native_row": deepcopy(native),
           "reported_distance": None, "reported_pvalue": None, "counts_token": None,
           "shared_hashes": None, "compared_union_hashes": None, "diagnostics": issues}
    if not isinstance(native, list):
        _issue(issues, "native_row_array_required", prefix)
        return row
    if len(native) != 4:
        _issue(issues, "native_row_arity", prefix)
    for position in range(4):
        path = f"{prefix}[{position}]"
        if position >= len(native):
            _issue(issues, "missing_native_field", path)
            continue
        value = native[position]
        if position == 0:
            if isinstance(value, str) and value.strip():
                row["genome_id"] = value
            else:
                _issue(issues, "null_native_field" if value is None else "invalid_genome_id", path)
        elif position in (1, 2):
            field = "reported_distance" if position == 1 else "reported_pvalue"
            row[field] = _number(value, path, issues)
            if position == 2 and row[field] == 0:
                _issue(issues, "reported_pvalue_zero_precision_unknown", path, severity="warning")
        else:
            row["counts_token"] = deepcopy(value)
            if value is None:
                _issue(issues, "null_native_field", path)
                continue
            match = _COUNTS.fullmatch(value) if isinstance(value, str) else None
            if match is None:
                _issue(issues, "invalid_counts_token", path)
                continue
            try:
                shared, union = (int(item) for item in match.groups())
            except ValueError:
                _issue(issues, "counts_integer_conversion_unavailable", path)
                continue
            # Preserve both parsed observations even if their relationship is invalid.
            row["shared_hashes"], row["compared_union_hashes"] = shared, union
            if shared > union:
                _issue(issues, "shared_hashes_exceed_union", path)
            elif union == 0:
                _issue(issues, "zero_compared_union_hashes", path, severity="warning")
    return row


def _validate_request(request, mode, issues):
    if not isinstance(request, dict):
        _issue(issues, "native_request_object_required", "request")
        return
    if request.get("method") != METHODS.get(mode):
        _issue(issues, "request_method_mode_mismatch", "request.method")
    args = request.get("params")
    if not isinstance(args, list) or len(args) != 8:
        _issue(issues, "eight_native_arguments_required", "request.params")
        return
    operand = args[0]
    if not isinstance(operand, str) or not operand.strip():
        _issue(issues, "query_identifier_required", "request.params[0]")
    elif mode == "fasta":
        # This checks Workspace syntax, not existence/access or local path resolution.
        parts = operand.split("/")
        if (not operand.startswith("/") or len(parts) < 4
                or any(part in ("", ".", "..") for part in parts[1:])
                or any(char in operand for char in "\r\n\x00")):
            _issue(issues, "workspace_fasta_path_required", "request.params[0]")
    for index in (1, 2):
        _number(args[index], f"request.params[{index}]", issues)
    for index in range(3, 8):
        # Native flags are integer truth values, not a newly invented enum.
        value = args[index]
        if type(value) is not int or (index == 3 and value < 0):
            _issue(issues, "native_integer_argument_required", f"request.params[{index}]")


def parse_minhash_result(value, *, mode, request, provenance):
    """Preserve and parse every native row; return ``{status, sheet, diagnostics}``.

    ``ok`` means format/cells parsed, not a complete search or a working service.
    ``partial`` retains usable associated cells beside missing/invalid cells.
    ``invalid`` identifies a bad outer contract or no usable associated cells.
    Empty arrays parse successfully but have unknown scientific completeness.
    Provenance is copied structured data; it never supplies missing measurements.
    """
    issues = []
    sheet = {"schema": SHEET_SCHEMA, "mode": deepcopy(mode),
             "request": deepcopy(request), "provenance": deepcopy(provenance),
             "native_result": deepcopy(value), "rows": [],
             "search_metadata": {"population_size": None, "reference_release": None,
                                 "truncated": None, "kmer_length": None,
                                 "hash_seed": None, "sketch_size": None}}
    if not isinstance(mode, str) or mode not in METHODS:
        _issue(issues, "unsupported_minhash_mode", "mode")
    else:
        _validate_request(request, mode, issues)
    if not _structured(provenance):
        _issue(issues, "structured_provenance_required", "provenance")
    if not isinstance(value, list):
        _issue(issues, "native_result_array_required", "native_result")
        return {"status": "invalid", "sheet": sheet, "diagnostics": issues}
    outer_invalid = any(item["severity"] == "error" for item in issues)
    sheet["rows"] = [_read_row(native, index) for index, native in enumerate(value)]
    for row in sheet["rows"]:
        issues.extend(deepcopy(row["diagnostics"]))
    if not value:
        _issue(issues, "empty_result_completeness_unknown", "native_result", severity="warning")
    usable = any(row["genome_id"] is not None and any(
        row[field] is not None for field in ("reported_distance", "reported_pvalue", "shared_hashes"))
        for row in sheet["rows"])
    errors = any(item["severity"] == "error" for item in issues)
    status = "invalid" if outer_invalid or (value and errors and not usable) else (
        "partial" if errors else "ok")
    return {"status": status, "sheet": sheet, "diagnostics": issues}


def _same(left, right):
    """JSON equality including bool/int, int/float and raw string distinctions."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    if isinstance(left, float) and math.isnan(left) and math.isnan(right):
        return True  # Preserve already diagnosed nonfinite native values.
    return left == right


def _metadata_index(metadata, rows, issues):
    grouped = {}
    if metadata is None:
        return grouped
    if not isinstance(metadata, list):
        _issue(issues, "pair_metadata_array_required", "pair_metadata")
        return grouped
    for index, record in enumerate(metadata):
        path = f"pair_metadata[{index}]"
        if not isinstance(record, dict):
            _issue(issues, "pair_metadata_object_required", path)
            continue
        ordinal, genome = record.get("row_index"), record.get("genome_id")
        if type(ordinal) is not int or not 0 <= ordinal < len(rows):
            _issue(issues, "pair_metadata_row_index_mismatch", path + ".row_index")
            continue
        if not isinstance(genome, str) or genome != rows[ordinal]["genome_id"]:
            _issue(issues, "pair_metadata_genome_id_mismatch", path + ".genome_id")
            continue
        grouped.setdefault((ordinal, genome), []).append((index, record))
    return grouped


def _calculate_distance(shared, union, k, issues, path):
    if shared == 0:
        return 1.0, None
    if shared == union:
        return 0.0, 0.0
    # log1p form of -log(2*j/(1+j)) avoids cancellation near full overlap.
    try:
        numerator = math.log1p((union - shared) / (2 * shared))
    except OverflowError:
        numerator = math.log(union + shared) - math.log(2 * shared)
    try:
        raw = numerator / k
    except OverflowError:
        _issue(issues, "distance_numeric_range_unsupported", path)
        return None, None
    if raw > 1:
        _issue(issues, "distance_saturated_at_one", path, severity="warning")
    if raw == 0:
        _issue(issues, "distance_underflow_or_rounding", path, severity="warning")
    return min(1.0, raw), raw


def _calculate_pvalue(shared, union, metadata, inputs, issues, path):
    k, query, reference, alphabet = (metadata[field] for field in _METADATA_FIELDS)
    try:
        log_space = k * math.log(alphabet)
    except OverflowError:
        _issue(issues, "null_model_numeric_range_unsupported", path)
        return None
    if not math.isfinite(log_space):
        _issue(issues, "null_model_numeric_range_unsupported", path)
        return None
    log_q, log_r = log_space - math.log(query), log_space - math.log(reference)
    # Algebraically j_random = 1/(1 + A/query + A/reference). Avoid multiplying
    # tiny r_i, which can underflow although j_random itself is representable.
    log_j = -float(logsumexp([0.0, log_q, log_r]))
    random_j = math.exp(log_j)
    try:
        space = float(alphabet) ** k
    except OverflowError:
        space = None
    inputs["null_model"] = {
        "kmer_space": space, "log_kmer_space": log_space,
        "query_random_kmer_probability": float(expit(-log_q)),
        "reference_random_kmer_probability": float(expit(-log_r)),
        "random_jaccard": random_j, "log_random_jaccard": log_j,
    }
    if space is None:
        _issue(issues, "kmer_space_overflow_log_calculation_used", path, severity="warning")
    if random_j == 0:
        _issue(issues, "random_jaccard_underflow", path, severity="warning")
    elif random_j == 1:
        _issue(issues, "random_jaccard_rounded_to_one", path, severity="warning")
    if shared == 0:
        return 1.0  # Native x=0 special case; all explicit metadata still retained.
    if union > 2**53:
        _issue(issues, "binomial_integer_precision_unsupported", path)
        return None
    probability = float(binom.sf(shared - 1, union, random_j))
    if not math.isfinite(probability):
        _issue(issues, "binomial_tail_unavailable", path)
        return None
    if probability == 0:
        _issue(issues, "recomputed_pvalue_underflow", path, severity="warning")
    elif probability == 1:
        _issue(issues, "recomputed_pvalue_rounded_to_one", path, severity="warning")
    return probability


def calculate_minhash_shared_hash_fraction(shared_hashes, compared_union_hashes,
                                          *, row_identity_available: bool) -> float | None:
    """Return the sampled hash-union fraction for an identified valid pair.

    No nominal sketch size, base coverage or annotation probability is implied.
    Unavailable identity, invalid counts and a zero denominator return None.
    Python's original division and its rounding/underflow behavior are retained;
    the full calculator owns the corresponding diagnostic records.
    """
    if (row_identity_available is not True
            or type(shared_hashes) is not int or type(compared_union_hashes) is not int
            or not 0 <= shared_hashes <= compared_union_hashes
            or compared_union_hashes <= 0):
        return None
    return shared_hashes / compared_union_hashes


def calculate_minhash_components(sheet, *, pair_metadata=None):
    """Calculate independent quantities from saved cells and explicit pair inputs.

    Metadata fields are positive integers and structured provenance, with no
    defaults. Missing lengths/alphabet prevent only the p-value; missing k also
    prevents distance. No-overlap still requires the declared inputs. A zero
    union denominator leaves all derived quantities unavailable. Duplicate
    metadata associations are ambiguous even if their contents are identical.
    SciPy's binomial survival function evaluates P[X >= shared_hashes] directly.
    """
    issues = []
    result = {"schema": COMPONENTS_SCHEMA, "rows": [], "diagnostics": issues}
    if not isinstance(sheet, dict) or sheet.get("schema") != SHEET_SCHEMA:
        _issue(issues, "minhash_sheet_required", "sheet.schema")
        return result
    parsed = parse_minhash_result(sheet.get("native_result"), mode=sheet.get("mode"),
                                  request=sheet.get("request"), provenance=sheet.get("provenance"))
    expected = parsed["sheet"]["rows"]
    rows = sheet.get("rows")
    if not isinstance(rows, list) or len(rows) != len(expected):
        _issue(issues, "sheet_native_row_count_mismatch", "sheet.rows")
        return result
    outer_issues = [item for item in parsed["diagnostics"]
                    if item["path"] in ("mode", "provenance", "native_result")
                    or item["path"].startswith("request")]
    if any(item["severity"] == "error" for item in outer_issues):
        issues.extend(deepcopy(parsed["diagnostics"]))
        return result
    issues.extend(deepcopy(outer_issues))
    grouped = _metadata_index(pair_metadata, expected, issues)
    for ordinal, (row, native) in enumerate(zip(rows, expected)):
        path = f"rows[{ordinal}]"
        row_issues = deepcopy(native["diagnostics"])
        inputs = {"shared_hashes": native["shared_hashes"],
                  "compared_union_hashes": native["compared_union_hashes"],
                  **{field: None for field in _METADATA_FIELDS},
                  "pair_metadata": None, "null_model": None}
        calculated = {"row_index": ordinal, "genome_id": native["genome_id"],
                      "reported_distance": native["reported_distance"],
                      "reported_pvalue": native["reported_pvalue"],
                      "shared_hash_fraction": None, "recomputed_distance": None,
                      "unsaturated_distance": None, "recomputed_pvalue": None,
                      "calculation_inputs": inputs, "diagnostics": row_issues}
        result["rows"].append(calculated)
        # Validate saved cells against their retained row, including associations.
        if not isinstance(row, dict) or any(
                not _same(row.get(field), value) for field, value in native.items()
                if field != "diagnostics"):
            _issue(row_issues, "sheet_native_row_mismatch", path)
            issues.extend(deepcopy(row_issues))
            continue
        matches = grouped.get((ordinal, native["genome_id"]), [])
        if len(matches) > 1:
            inputs["pair_metadata_candidates"] = [deepcopy(record) for _, record in matches]
            _issue(row_issues, "ambiguous_pair_metadata", path + ".calculation_inputs")
        elif matches:
            index, record = matches[0]
            inputs["pair_metadata"] = deepcopy(record)
            meta_path = f"pair_metadata[{index}]"
            if not _structured(record.get("provenance")):
                _issue(row_issues, "structured_metadata_provenance_required", meta_path + ".provenance")
            else:
                for field in _METADATA_FIELDS:
                    value = record.get(field)
                    if value is None:
                        _issue(row_issues, "missing_calculation_input", meta_path + "." + field)
                    elif type(value) is not int or value <= 0:
                        _issue(row_issues, "positive_integer_metadata_required", meta_path + "." + field)
                    else:
                        inputs[field] = value
        else:
            _issue(row_issues, "pair_metadata_missing", path + ".calculation_inputs")
        shared, union = inputs["shared_hashes"], inputs["compared_union_hashes"]
        if native["genome_id"] is None:
            _issue(row_issues, "row_identity_unavailable", path + ".genome_id")
        elif shared is None or union is None or shared > union:
            _issue(row_issues, "valid_hash_counts_required", path + ".calculation_inputs")
        elif union == 0:
            _issue(row_issues, "zero_union_calculations_unavailable", path + ".calculation_inputs")
        else:
            fraction = calculate_minhash_shared_hash_fraction(
                shared, union, row_identity_available=native["genome_id"] is not None)
            calculated["shared_hash_fraction"] = fraction
            if (fraction == 0 and shared > 0) or (fraction == 1 and shared < union):
                _issue(row_issues, "shared_fraction_underflow_or_rounding", path, severity="warning")
            if inputs["kmer_length"] is not None:
                distance, raw = _calculate_distance(shared, union, inputs["kmer_length"],
                                                     row_issues, path + ".recomputed_distance")
                calculated.update(recomputed_distance=distance, unsaturated_distance=raw)
            if all(inputs[field] is not None for field in _METADATA_FIELDS):
                calculated["recomputed_pvalue"] = _calculate_pvalue(
                    shared, union, inputs, inputs, row_issues, path + ".recomputed_pvalue")
        issues.extend(deepcopy(row_issues))
    return result


__all__ = ["parse_minhash_result", "calculate_minhash_components",
           "calculate_minhash_shared_hash_fraction", "MINHASH_DIAGNOSTIC_CODES"]
