"""Pure requested facts from frozen direct-MinHash publications.

The host must authenticate each original acquisition/publication receipt before
supplying ``{source_ref, grading}``. Passing JSON or a syntactically valid source
ID cannot establish custody. This module validates supplied relationships and
copies saved quantities; it does not read a store, acquire, parse again, regrade,
choose work, render a prompt, or assign credit.

The v1 publication contains C2 outputs calculated without pair metadata. The v2
envelope retains explicit calculation inputs with the same sheet/components.
Checks against native cells, supplied inputs and saved operands detect
inconsistent records; they never replace saved values or reconstruct a grade.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import math
import re

from .bvbrc_analysis_protocol import prepare_rpc_request
from .bvbrc_minhash_contracts import validate_minhash_publication_inputs
from .bvbrc_minhash_grader import (
    MINHASH_DIAGNOSTIC_CODES, calculate_minhash_shared_hash_fraction,
)
from .domain import identity


_MATCHES = "bvbrc_minhash_matches"
_COUNTS = "bvbrc_minhash_counts"
_CALCULATIONS = "bvbrc_minhash_calculations"
_CALCULATION_DIAGNOSTICS = "bvbrc_minhash_calculation_diagnostics"
_SOURCES = (_MATCHES, _COUNTS, _CALCULATIONS, _CALCULATION_DIAGNOSTICS)
_OPERANDS = ("query", "max_pvalue", "max_distance", "max_hits", "include_reference",
             "include_representative", "bacterial", "viral")
_METADATA = ("kmer_length", "query_length", "reference_length", "alphabet_size")
_NATIVE_NUMBERS = ("reported_distance", "reported_pvalue")
_HASH_COUNTS = ("shared_hashes", "compared_union_hashes")
_SOURCE_ID = re.compile(r"source_[a-f0-9]{24,64}\Z")
# The native genome-ID rule used by C1, not a new communication format.
_GENOME_ID = re.compile(r"[0-9]+\.[0-9]+\Z")
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_COUNT_TOKEN = re.compile(r"([0-9]+)/([0-9]+)\Z")
_DIAGNOSTIC_PATH = r"^[a-z_]+(?:\[[0-9]+\])*(?:\.[a-z_]+(?:\[[0-9]+\])*)*$"
_REF = {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"}
_STATUS = {"type": "string", "enum": ["ok", "partial", "invalid"]}


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def minhash_fact_sources() -> dict:
    """Return detached recorded-source declarations for the closed form guard."""
    match = _object({
        "source_ref": _REF,
        "row_index": {"type": "integer", "minimum": 0},
        "genome_id": {"type": ["string", "null"], "format": "identifier",
                      "x-reference-namespace": "bvbrc_minhash_genome"},
        **{name: {"type": ["number", "null"], "minimum": 0, "maximum": 1}
           for name in (*_NATIVE_NUMBERS, "shared_hash_fraction")},
        **{name: {"type": ["integer", "null"], "minimum": 0} for name in _HASH_COUNTS},
        "parse_status": _STATUS,
    })
    count = _object({
        "source_ref": _REF,
        "returned_row_count": {"type": "integer", "minimum": 0},
        "parse_status": _STATUS,
        "population_size": {"type": "null"},
        "truncated": {"type": "null"},
    })
    calculation = _object({
        "source_ref": _REF,
        "row_index": {"type": "integer", "minimum": 0},
        "genome_id": {"type": ["string", "null"], "format": "identifier",
                      "x-reference-namespace": "bvbrc_minhash_genome"},
        **{name: {"type": ["number", "null"], "minimum": 0, "maximum": 1}
           for name in ("shared_hash_fraction", "recomputed_distance", "recomputed_pvalue")},
        "unsaturated_distance": {"type": ["number", "null"], "minimum": 0},
        **{name: {"type": ["integer", "null"], "minimum": 1} for name in _METADATA},
        "native_parameter_equivalence": {"type": "string", "enum": ["unestablished"]},
        "parse_status": _STATUS,
        "diagnostic_codes": {"type": "array", "items": {
            "type": "string", "enum": sorted(MINHASH_DIAGNOSTIC_CODES)}},
    })
    diagnostic = _object({
        "source_ref": _REF,
        "code": {"type": "string", "enum": sorted(MINHASH_DIAGNOSTIC_CODES)},
        "path": {"type": "string", "pattern": _DIAGNOSTIC_PATH},
        "severity": {"type": "string", "enum": ["error", "warning"]},
    })
    return deepcopy({
        _MATCHES: {"type": "array", "meaning":
            "Original ordered MinHash matches, native distance/p-value and sampled shared-hash quantities; nulls preserve unavailable cells.",
            "report_schema": {"type": "array", "items": match, "x-source": _MATCHES}},
        _COUNTS: {"type": "array", "meaning":
            "Actual returned array length and acquisition parse status; neither search population nor search completeness is known.",
            "report_schema": {"type": "array", "items": count, "x-source": _COUNTS}},
        _CALCULATIONS: {"type": "array", "meaning":
            "Saved sampled hash fractions, distance and p-value recalculations with their explicit pair inputs; native parameter equivalence remains unestablished and native parse status is separate from calculation availability.",
            "report_schema": {"type": "array", "items": calculation, "x-source": _CALCULATIONS}},
        _CALCULATION_DIAGNOSTICS: {"type": "array", "meaning":
            "Saved calculator diagnostics in original order, including unmatched pair metadata that cannot be assigned to a native result row.",
            "report_schema": {"type": "array", "items": diagnostic, "x-source": _CALCULATION_DIAGNOSTICS}},
    })


def _require(condition, code, path):
    if not condition:
        raise ValueError(f"bvbrc_minhash_projection_invalid:{code}:{path}")


def _fields(value, names, path):
    _require(type(value) is dict and set(value) == set(names), "closed_fields", path)


def _finite_json(value):
    active = set()

    def visit(item, path):
        kind = type(item)
        if item is None or kind in (str, int, bool):
            return
        if kind is float:
            _require(math.isfinite(item), "nonfinite_number", path)
            return
        _require(kind in (dict, list) and id(item) not in active, "plain_json_required", path)
        active.add(id(item))
        try:
            if kind is dict:
                _require(all(type(key) is str for key in item), "json_key", path)
                for key, child in item.items():
                    visit(child, f"{path}.{key}")
            else:
                for index, child in enumerate(item):
                    visit(child, f"{path}[{index}]")
        finally:
            active.remove(id(item))

    try:
        visit(value, "qualified_results")
    except RecursionError as exc:
        raise ValueError("bvbrc_minhash_projection_invalid:plain_json_required:depth") from exc


def _same(left, right):
    """Do not equate bool/int, int/float, or native numeric string/number."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _nullable_number(value, path, *, integer=False, upper=1):
    if value is None:
        return
    _require(type(value) is int if integer else type(value) in (int, float), "numeric_cell", path)
    _require(value >= 0 and (integer or upper is None or value <= upper), "numeric_range", path)


def _diagnostics(value, path, *, typed=False):
    _require(type(value) is list, "diagnostics_array", path)
    for index, row in enumerate(value):
        loc = f"{path}[{index}]"
        _fields(row, ("code", "path", "severity"), loc)
        _require(type(row["code"]) is str and bool(row["code"])
                 and type(row["path"]) is str and bool(row["path"])
                 and row["severity"] in ("error", "warning"), "diagnostic_fields", loc)
        if typed:
            _require(row["code"] in MINHASH_DIAGNOSTIC_CODES
                     and re.fullmatch(_DIAGNOSTIC_PATH, row["path"]) is not None,
                     "typed_diagnostic_fields", loc)


def _native_number_agrees(saved, native):
    """Validate the saved C2 conversion, without producing a new sheet cell."""
    expected = native
    if type(native) is str:
        if _NUMBER.fullmatch(native) is None:
            return saved is None
        expected = float(native)
        if not math.isfinite(expected) or Decimal(native) < 0:
            return saved is None
    elif type(native) not in (int, float):
        return saved is None
    if not 0 <= expected <= 1:
        return saved is None
    return _same(saved, expected)


def _validate_sheet_row(row, native, index, path):
    _fields(row, ("row_index", "genome_id", "native_row", *_NATIVE_NUMBERS,
                  "counts_token", *_HASH_COUNTS, "diagnostics"), path)
    _require(type(row["row_index"]) is int and row["row_index"] == index, "sheet_row_index", path)
    _require(_same(row["native_row"], native), "native_row_association", path)
    _diagnostics(row["diagnostics"], path + ".diagnostics")
    cells = native if type(native) is list else []
    genome = cells[0] if cells and type(cells[0]) is str and cells[0].strip() else None
    _require(_same(row["genome_id"], genome), "native_genome_id", path + ".genome_id")
    for position, name in enumerate(_NATIVE_NUMBERS, 1):
        _nullable_number(row[name], path + "." + name)
        value = cells[position] if position < len(cells) else None
        _require(_native_number_agrees(row[name], value), "native_number_mismatch", path + "." + name)
    token = cells[3] if len(cells) > 3 else None
    _require(_same(row["counts_token"], token), "counts_token_mismatch", path + ".counts_token")
    match = _COUNT_TOKEN.fullmatch(token) if type(token) is str else None
    counts = (None, None)
    if match:
        try:
            counts = tuple(int(value) for value in match.groups())
        except ValueError:
            pass  # C2 retains the token and qualifies unavailable integer conversion.
    for name, value in zip(_HASH_COUNTS, counts):
        _nullable_number(row[name], path + "." + name, integer=True)
        _require(_same(row[name], value), "native_count_mismatch", path + "." + name)
    malformed = (type(native) is not list or len(cells) != 4 or genome is None
                 or any(row[name] is None for name in (*_NATIVE_NUMBERS, *_HASH_COUNTS))
                 or counts[0] is not None and counts[0] > counts[1])
    has_error = any(item["severity"] == "error" for item in row["diagnostics"])
    _require(has_error == malformed, "row_parse_diagnostics", path + ".diagnostics")


def _metadata_associations(metadata, rows):
    """Check saved joins, retaining unmatched diagnostics in input-list order."""
    grouped, unmatched = {}, []
    for index, record in enumerate(metadata):
        ordinal, genome = record["row_index"], record["genome_id"]
        if ordinal >= len(rows):
            field, code = "row_index", "pair_metadata_row_index_mismatch"
        elif genome != rows[ordinal]["genome_id"]:
            field, code = "genome_id", "pair_metadata_genome_id_mismatch"
        else:
            grouped.setdefault((ordinal, genome), []).append((index, record))
            continue
        unmatched.append({"code": code, "path": f"pair_metadata[{index}].{field}", "severity": "error"})
    return grouped, unmatched


def _validate_calculation_availability(row, inputs, path):
    """Validate saved availability/shape, without reproducing scientific math."""
    for name in ("recomputed_distance", "recomputed_pvalue"):
        _nullable_number(row[name], path + "." + name)
    _nullable_number(row["unsaturated_distance"], path + ".unsaturated_distance", upper=None)
    codes = {item["code"] for item in row["diagnostics"]}
    counts_available = row["shared_hash_fraction"] is not None
    distance_available = counts_available and inputs["kmer_length"] is not None
    distance_failed = "distance_numeric_range_unsupported" in codes
    _require((row["recomputed_distance"] is not None) == (distance_available and not distance_failed),
             "distance_availability", path + ".recomputed_distance")
    raw_available = distance_available and not distance_failed and inputs["shared_hashes"] != 0
    _require((row["unsaturated_distance"] is not None) == raw_available,
             "distance_availability", path + ".unsaturated_distance")

    pvalue_inputs = counts_available and all(inputs[name] is not None for name in _METADATA)
    model_failed = "null_model_numeric_range_unsupported" in codes
    model = inputs["null_model"]
    _require((model is not None) == (pvalue_inputs and not model_failed),
             "null_model_availability", path + ".calculation_inputs.null_model")
    if model is not None:
        location = path + ".calculation_inputs.null_model"
        _fields(model, ("kmer_space", "log_kmer_space", "query_random_kmer_probability",
                        "reference_random_kmer_probability", "random_jaccard", "log_random_jaccard"), location)
        _nullable_number(model["kmer_space"], location + ".kmer_space", upper=None)
        _require(model["kmer_space"] is None or model["kmer_space"] >= 1,
                 "null_model_range", location + ".kmer_space")
        for name in ("log_kmer_space", "query_random_kmer_probability",
                     "reference_random_kmer_probability", "random_jaccard"):
            _require(model[name] is not None, "null_model_cell", location + "." + name)
            _nullable_number(model[name], location + "." + name,
                             upper=None if name == "log_kmer_space" else 1)
        _require(type(model["log_random_jaccard"]) in (int, float)
                 and model["log_random_jaccard"] <= 0, "null_model_cell", location + ".log_random_jaccard")
        _require((model["kmer_space"] is None) == ("kmer_space_overflow_log_calculation_used" in codes),
                 "null_model_availability", location + ".kmer_space")
    pvalue_failed = bool(codes & {"null_model_numeric_range_unsupported",
                                 "binomial_integer_precision_unsupported", "binomial_tail_unavailable"})
    _require((row["recomputed_pvalue"] is not None) == (pvalue_inputs and not pvalue_failed),
             "pvalue_availability", path + ".recomputed_pvalue")


def _validate_metadata_inputs(row, saved, matches, index, path):
    inputs = row["calculation_inputs"]
    names = (*_HASH_COUNTS, *_METADATA, "pair_metadata", "null_model")
    if len(matches) > 1:
        names += ("pair_metadata_candidates",)
    _fields(inputs, names, path + ".calculation_inputs")
    required_diagnostics = []
    if len(matches) == 1:
        metadata_index, record = matches[0]
        _require(_same(inputs["pair_metadata"], record), "component_metadata_association",
                 path + ".calculation_inputs.pair_metadata")
        for name in _METADATA:
            _require(_same(inputs[name], record[name]), "component_metadata_operand",
                     path + ".calculation_inputs." + name)
            if record[name] is None:
                required_diagnostics.append({"code": "missing_calculation_input",
                    "path": f"pair_metadata[{metadata_index}].{name}", "severity": "error"})
    else:
        _require(all(inputs[name] is None for name in (*_METADATA, "pair_metadata")),
                 "component_metadata_unavailable", path + ".calculation_inputs")
        if matches:
            _require(_same(inputs["pair_metadata_candidates"], [record for _, record in matches]),
                     "component_metadata_candidates", path + ".calculation_inputs.pair_metadata_candidates")
        required_diagnostics.append({"code": "ambiguous_pair_metadata" if matches else "pair_metadata_missing",
            "path": f"rows[{index}].calculation_inputs", "severity": "error"})
    start = len(saved["diagnostics"])
    end = start + len(required_diagnostics)
    _require(_same(row["diagnostics"][start:end], required_diagnostics),
             "component_metadata_diagnostics", path + ".diagnostics")
    for item in row["diagnostics"][end:]:
        _require(item["path"] == f"rows[{index}]" or item["path"].startswith(f"rows[{index}]."),
                 "component_diagnostic_association", path + ".diagnostics")
    _validate_calculation_availability(row, inputs, path)


def _validate_component(row, saved, index, path, *, matches=None, typed_diagnostics=False):
    _fields(row, ("row_index", "genome_id", *_NATIVE_NUMBERS, "shared_hash_fraction",
                  "recomputed_distance", "unsaturated_distance", "recomputed_pvalue",
                  "calculation_inputs", "diagnostics"), path)
    for name in ("row_index", "genome_id", *_NATIVE_NUMBERS):
        _require(_same(row[name], saved[name]), "component_row_association", path + "." + name)
    _diagnostics(row["diagnostics"], path + ".diagnostics", typed=typed_diagnostics)
    _require(_same(row["diagnostics"][:len(saved["diagnostics"])], saved["diagnostics"]),
             "component_parse_diagnostics", path + ".diagnostics")
    inputs = row["calculation_inputs"]
    if matches is None:
        _fields(inputs, (*_HASH_COUNTS, *_METADATA, "pair_metadata", "null_model"), path + ".calculation_inputs")
        for name in (*_METADATA, "pair_metadata", "null_model"):
            _require(inputs[name] is None, "publication_metadata_unavailable", path + ".calculation_inputs." + name)
        for name in ("recomputed_distance", "unsaturated_distance", "recomputed_pvalue"):
            _require(row[name] is None, "publication_metadata_unavailable", path + "." + name)
    else:
        _validate_metadata_inputs(row, saved, matches, index, path)
    for name in _HASH_COUNTS:
        _require(_same(inputs[name], saved[name]), "component_count_operands", path + ".calculation_inputs." + name)
    shared, union = (saved[name] for name in _HASH_COUNTS)
    fraction = row["shared_hash_fraction"]
    _nullable_number(fraction, path + ".shared_hash_fraction")
    expected_fraction = calculate_minhash_shared_hash_fraction(
        shared, union, row_identity_available=saved["genome_id"] is not None)
    _require(_same(fraction, expected_fraction),
             "shared_fraction_operands", path + ".shared_hash_fraction")
    if matches is None:
        _require(any(item == {"code": "pair_metadata_missing", "path": f"rows[{index}].calculation_inputs",
                              "severity": "error"} for item in row["diagnostics"]),
                 "missing_metadata_diagnostic", path + ".diagnostics")


def _validate_grading(grading, path, *, typed_diagnostics=False):
    v2 = type(grading) is dict and grading.get("schema") == "bvbrc_minhash_grading_v2"
    fields = ("schema", "request", "rpc_request", "selector", "parse_status", "sheet", "components", "diagnostics")
    _fields(grading, fields + (("publication_inputs",) if v2 else ()), path)
    _require(grading["schema"] in ("bvbrc_minhash_grading_v1", "bvbrc_minhash_grading_v2"),
             "grading_schema", path + ".schema")
    if not v2:
        _require(grading["selector"] == {}, "selector", path + ".selector")
    _require(grading["parse_status"] in ("ok", "partial", "invalid"), "parse_status", path + ".parse_status")
    request, rpc = grading["request"], grading["rpc_request"]
    _fields(request, ("mode", *_OPERANDS), path + ".request")
    _require(request["mode"] in ("genome", "fasta"), "mode", path + ".request.mode")
    _fields(rpc, ("version", "method", "params", "id"), path + ".rpc_request")
    method = f"Minhash.compute_genome_distance_for_{request['mode']}2"
    try:
        expected = prepare_rpc_request(method, [request[name] for name in _OPERANDS],
                                       request_id=identity("minhash_rpc", request))
    except ValueError as exc:
        raise ValueError(f"bvbrc_minhash_projection_invalid:native_request:{path}.request:{exc}") from exc
    _require(_same(rpc, expected), "rpc_request_identity", path + ".rpc_request")
    if request["mode"] == "fasta":
        parts = request["query"].split("/")
        _require(request["query"].startswith("/") and len(parts) >= 4
                 and all(part not in ("", ".", "..") for part in parts[1:]),
                 "workspace_fasta_path", path + ".request.query")
    publication_inputs = None
    if v2:
        publication_inputs = validate_minhash_publication_inputs(
            grading["publication_inputs"], request=request, selector=grading["selector"])
    sheet, components = grading["sheet"], grading["components"]
    _fields(sheet, ("schema", "mode", "request", "provenance", "native_result", "rows", "search_metadata"), path + ".sheet")
    _require(sheet["schema"] == "bvbrc_minhash_sheet_v1", "sheet_schema", path + ".sheet.schema")
    _require(_same(sheet["mode"], request["mode"]) and _same(sheet["request"], rpc),
             "sheet_request_identity", path + ".sheet.request")
    _require(type(sheet["provenance"]) in (dict, list), "structured_provenance", path + ".sheet.provenance")
    _fields(sheet["search_metadata"], ("population_size", "reference_release", "truncated",
                                      "kmer_length", "hash_seed", "sketch_size"), path + ".sheet.search_metadata")
    _require(all(value is None for value in sheet["search_metadata"].values()),
             "search_metadata_unavailable", path + ".sheet.search_metadata")
    _fields(components, ("schema", "rows", "diagnostics"), path + ".components")
    _require(components["schema"] == "bvbrc_minhash_components_v1", "components_schema", path + ".components.schema")
    native, rows, calculated = sheet["native_result"], sheet["rows"], components["rows"]
    _require(type(native) is list and type(rows) is list and type(calculated) is list,
             "row_arrays", path)
    _require(len(native) == len(rows) == len(calculated), "row_count_association", path)
    for index, (row, original) in enumerate(zip(rows, native)):
        _validate_sheet_row(row, original, index, f"{path}.sheet.rows[{index}]")
    grouped, unmatched = ({}, []) if publication_inputs is None else _metadata_associations(
        publication_inputs["pair_metadata"], rows)
    if publication_inputs is not None and publication_inputs["saved_result"] is not None:
        _require(_same(sheet, publication_inputs["saved_result"]["sheet"]),
                 "saved_sheet_association", path + ".sheet")
    for index, (row, component) in enumerate(zip(rows, calculated)):
        _validate_component(component, row, index, f"{path}.components.rows[{index}]",
            matches=grouped.get((index, row["genome_id"]), []) if v2 else None,
            typed_diagnostics=v2 or typed_diagnostics)
    _diagnostics(grading["diagnostics"], path + ".diagnostics", typed=v2 or typed_diagnostics)
    _diagnostics(components["diagnostics"], path + ".components.diagnostics", typed=v2 or typed_diagnostics)
    empty = [{"code": "empty_result_completeness_unknown", "path": "native_result", "severity": "warning"}] if not rows else []
    _require(_same(grading["diagnostics"], [item for row in rows for item in row["diagnostics"]] + empty),
             "parse_diagnostics_association", path + ".diagnostics")
    _require(_same(components["diagnostics"], empty + unmatched + [item for row in calculated for item in row["diagnostics"]]),
             "component_diagnostics_association", path + ".components.diagnostics")
    errors = any(item["severity"] == "error" for item in grading["diagnostics"])
    usable = any(row["genome_id"] is not None and any(row[name] is not None
                 for name in (*_NATIVE_NUMBERS, "shared_hashes")) for row in rows)
    status = "invalid" if rows and errors and not usable else "partial" if errors else "ok"
    _require(grading["parse_status"] == status, "parse_status_consistency", path + ".parse_status")
    return rows, calculated


def project_minhash_facts(qualified_results, *, requested_sources) -> dict:
    """Copy only requested fact families from host-qualified frozen envelopes.

    Native order, duplicate matches, zero and null remain distinct. Row status
    qualifies the projected cells and tool-specific identifier; the count status
    remains the saved acquisition status. No source-global access or receipt
    authentication is performed by this supplied-data-only function.
    """
    _require(type(requested_sources) in (list, tuple, set, frozenset), "requested_sources", "requested_sources")
    _require(all(type(name) is str and name in _SOURCES for name in requested_sources),
             "unknown_requested_source", "requested_sources")
    _require(len(set(requested_sources)) == len(requested_sources), "duplicate_requested_source", "requested_sources")
    _require(type(qualified_results) is list, "qualified_results_array", "qualified_results")
    _finite_json(qualified_results)
    facts = {name: [] for name in _SOURCES if name in requested_sources}
    for index, qualified in enumerate(qualified_results):
        path = f"qualified_results[{index}]"
        _fields(qualified, ("source_ref", "grading"), path)
        source = qualified["source_ref"]
        _require(type(source) is str and _SOURCE_ID.fullmatch(source) is not None, "source_reference", path + ".source_ref")
        rows, components = _validate_grading(qualified["grading"], path + ".grading",
            typed_diagnostics=_CALCULATIONS in facts or _CALCULATION_DIAGNOSTICS in facts)
        if _COUNTS in facts:
            facts[_COUNTS].append({"source_ref": source, "returned_row_count": len(rows),
                "parse_status": qualified["grading"]["parse_status"], "population_size": None, "truncated": None})
        if _CALCULATION_DIAGNOSTICS in facts:
            facts[_CALCULATION_DIAGNOSTICS].extend({"source_ref": source, **deepcopy(item)}
                for item in qualified["grading"]["components"]["diagnostics"])
        if _MATCHES not in facts and _CALCULATIONS not in facts:
            continue
        for row, component in zip(rows, components):
            genome = row["genome_id"]
            if genome is not None and _GENOME_ID.fullmatch(genome) is None:
                genome = None
            cells = {name: row[name] for name in (*_NATIVE_NUMBERS, *_HASH_COUNTS)}
            cells["shared_hash_fraction"] = component["shared_hash_fraction"]
            incomplete = genome is None or any(item["severity"] == "error" for item in row["diagnostics"])
            status = ("partial" if any(value is not None for value in cells.values()) else "invalid") if incomplete else "ok"
            if _MATCHES in facts:
                facts[_MATCHES].append({"source_ref": source, "row_index": row["row_index"],
                                       "genome_id": genome, **cells, "parse_status": status})
            if _CALCULATIONS in facts:
                facts[_CALCULATIONS].append({"source_ref": source, "row_index": row["row_index"],
                    "genome_id": genome,
                    **{name: component[name] for name in ("shared_hash_fraction", "recomputed_distance",
                        "unsaturated_distance", "recomputed_pvalue")},
                    **{name: component["calculation_inputs"][name] for name in _METADATA},
                    "native_parameter_equivalence": "unestablished", "parse_status": status,
                    "diagnostic_codes": [item["code"] for item in component["diagnostics"]]})
    return facts


__all__ = ["minhash_fact_sources", "project_minhash_facts"]
